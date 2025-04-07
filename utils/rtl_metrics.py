# utils/rtl_metrics.py

import os
import json
import networkx as nx
from pyvis.network import Network
import tempfile
from pyverilog.vparser.parser import parse
from pyverilog.vparser.ast import *
import streamlit.components.v1 as components
from graphviz import Digraph
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

metrics = {
    'modules': 0,
    'inputs': 0,
    'outputs': 0,
    'wires': 0,
    'regs': 0,
    'fsm_blocks': 0,
    'always_blocks': 0,
    'signal_widths': {},
    'unused_signals': [],
    'design_score': 0,
    'fan_in_out': {},
}

module_hierarchy = {}
signal_usage = {}
declared_signals = set()

def reset_metrics():
    global metrics, module_hierarchy, signal_usage, declared_signals
    metrics = {
        'modules': 0,
        'inputs': 0,
        'outputs': 0,
        'wires': 0,
        'regs': 0,
        'fsm_blocks': 0,
        'always_blocks': 0,
        'signal_widths': {},
        'unused_signals': [],
        'design_score': 0,
        'fan_in_out': {},
    }
    module_hierarchy = {}
    signal_usage = {}
    declared_signals = set()

def get_width(node):
    if node.width:
        msb = int(node.width.msb.value)
        lsb = int(node.width.lsb.value)
        return abs(msb - lsb) + 1
    return 1

def is_fsm(node):
    if isinstance(node, Always):
        for stmt in node.statement.statements:
            if isinstance(stmt, CaseStatement):
                return True
    return False

def count_ast_nodes(node, parent_module=None):
    if isinstance(node, ModuleDef):
        metrics['modules'] += 1
        current_module = node.name
        module_hierarchy[current_module] = []

        if node.portlist:
            for port in node.portlist.ports:
                if isinstance(port, Ioport):
                    first = port.first
                    width = get_width(first)
                    if isinstance(first, Input):
                        metrics['inputs'] += 1
                        metrics['signal_widths'][first.name] = width
                        declared_signals.add(first.name)
                    elif isinstance(first, Output):
                        metrics['outputs'] += 1
                        metrics['signal_widths'][first.name] = width
                        declared_signals.add(first.name)

        for item in node.items:
            count_ast_nodes(item, parent_module=current_module)

    elif isinstance(node, Decl):
        for decl in node.list:
            width = get_width(decl)
            metrics['signal_widths'][decl.name] = width
            declared_signals.add(decl.name)

            if isinstance(decl, Input):
                metrics['inputs'] += 1
            elif isinstance(decl, Output):
                metrics['outputs'] += 1
            elif isinstance(decl, Wire):
                metrics['wires'] += 1
            elif isinstance(decl, Reg):
                metrics['regs'] += 1

    elif isinstance(node, InstanceList):
        for inst in node.instances:
            if parent_module:
                module_hierarchy[parent_module].append(inst.module)

    elif isinstance(node, Always):
        metrics['always_blocks'] += 1
        if is_fsm(node):
            metrics['fsm_blocks'] += 1

    elif isinstance(node, Identifier):
        signal_usage[node.name] = signal_usage.get(node.name, 0) + 1

    if hasattr(node, 'children'):
        for child in node.children():
            count_ast_nodes(child, parent_module)

def compute_design_score():
    score = (
        metrics['modules'] * 10 +
        metrics['inputs'] * 2 +
        metrics['outputs'] * 2 +
        metrics['wires'] * 1 +
        metrics['regs'] * 2 +
        metrics['fsm_blocks'] * 5 +
        metrics['always_blocks'] * 3
    )
    metrics['design_score'] = score

def detect_unused_signals():
    for signal in declared_signals:
        if signal_usage.get(signal, 0) == 0:
            metrics['unused_signals'].append(signal)

def compute_fan_in_out():
    for signal, count in signal_usage.items():
        metrics['fan_in_out'][signal] = {
            'fan_out': count,
            'fan_in': 1 if signal in declared_signals else 0
        }

def analyze_verilog_file(verilog_path: str):
    reset_metrics()
    ast, _ = parse([verilog_path])
    count_ast_nodes(ast)
    compute_design_score()
    detect_unused_signals()
    compute_fan_in_out()
    for f in ["parser.out", "parsetab.py", "parsetab.pyc"]:
        if os.path.exists(f):
            os.remove(f)
    return metrics, module_hierarchy

def visualize_module_hierarchy_graph(module_hierarchy, title="Module Hierarchy"):
    st.subheader(f"🧩 {title} (Graph)")

    G = nx.DiGraph()

    for parent, children in module_hierarchy.items():
        for child in children:
            G.add_edge(parent, child)

    net = Network(height="400px", width="100%", directed=True)
    net.from_nx(G)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        html_path = tmp_file.name

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        components.html(html_content, height=500, scrolling=True)

    os.remove(html_path)  # Clean up

def visualize_rtl_metrics(file_name, metrics, module_hierarchy):
    st.markdown(f"### 📁 File: `{file_name}`")

    col1, col2, col3 = st.columns(3)
    col1.metric("Modules", metrics["modules"])
    col2.metric("Inputs", metrics["inputs"])
    col3.metric("Outputs", metrics["outputs"])

    col4, col5, col6 = st.columns(3)
    col4.metric("Wires", metrics["wires"])
    col5.metric("Regs", metrics["regs"])
    col6.metric("FSM Blocks", metrics["fsm_blocks"])

    col7, col8 = st.columns(2)
    col7.metric("Always Blocks", metrics["always_blocks"])
    col8.metric("Design Score", metrics["design_score"])

    # Signal Widths
    st.subheader("📏 Signal Widths")
    if metrics["signal_widths"]:
        df_widths = pd.DataFrame(list(metrics["signal_widths"].items()), columns=["Signal", "Width"])
        st.bar_chart(df_widths.set_index("Signal"))

    # Fan-in/Fan-out
    st.subheader("🔁 Fan-in / Fan-out")
    if metrics["fan_in_out"]:
        fan_df = pd.DataFrame([
            {"Signal": k, "Type": "Fan-in", "Value": v["fan_in"]}
            for k, v in metrics["fan_in_out"].items()
        ] + [
            {"Signal": k, "Type": "Fan-out", "Value": v["fan_out"]}
            for k, v in metrics["fan_in_out"].items()
        ])
        fan_chart = px.bar(fan_df, x="Signal", y="Value", color="Type", barmode="group")
        st.plotly_chart(fan_chart)

    # Unused Signals
    st.subheader("🚫 Unused Signals")
    unused = metrics.get("unused_signals")
    if unused:
        st.error(", ".join(unused))
    else:
        st.success("No unused signals 🎉")

    # Module Hierarchy (Graph)
    visualize_module_hierarchy_graph(module_hierarchy)
