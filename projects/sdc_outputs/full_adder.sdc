#-----------------------------------------------------------------------
# Synopsys Design Constraints (SDC) file for full_adder module
# Generated for a 100 MHz FPGA-based design
#-----------------------------------------------------------------------

#-----------------------------------------------------------------------
# Clock Definition
#-----------------------------------------------------------------------

# Assuming 'a', 'b', and 'cin' can all change every clock cycle, we can constrain them as clocks for analysis.
# However, in a real design, only one or possibly none of these might truly be a clock.  Adjust accordingly.

create_clock -period 10.000 -name clk_a -waveform {0.000 5.000} [get_ports a]
create_clock -period 10.000 -name clk_b -waveform {0.000 5.000} [get_ports b]
create_clock -period 10.000 -name clk_cin -waveform {0.000 5.000} [get_ports cin]

# Alternatively, if 'a', 'b', and 'cin' are NOT driven by clocks, you would need to specify the clock driving the upstream logic.
# Example, assuming an external clock named 'sys_clk' exists:
# create_clock -period 10.000 -name sys_clk -waveform {0.000 5.000} [get_ports sys_clk_port] # Assuming sys_clk is an input port
# set_input_delay -clock sys_clk -max 2.000 [get_ports {a b cin}]
# set_input_delay -clock sys_clk -min 0.500 [get_ports {a b cin}]

#-----------------------------------------------------------------------
# Input Delay Constraints
#-----------------------------------------------------------------------

# Relative to the clocks we just created
set_input_delay -clock clk_a -max 2.000 [get_ports a]
set_input_delay -clock clk_a -min 0.500 [get_ports a]

set_input_delay -clock clk_b -max 2.000 [get_ports b]
set_input_delay -clock clk_b -min 0.500 [get_ports b]

set_input_delay -clock clk_cin -max 2.000 [get_ports cin]
set_input_delay -clock clk_cin -min 0.500 [get_ports cin]

#-----------------------------------------------------------------------
# Output Delay Constraints
#-----------------------------------------------------------------------

# Relative to the clocks we just created
set_output_delay -clock clk_a -max 2.000 [get_ports sum]
set_output_delay -clock clk_a -min 0.500 [get_ports sum]

set_output_delay -clock clk_a -max 2.000 [get_ports cout]
set_output_delay -clock clk_a -min 0.500 [get_ports cout]

# Assuming sum and cout are synchronous to a, but any could be used.
# set_output_delay -clock clk_b -max 2.000 [get_ports {sum cout}]
# set_output_delay -clock clk_cin -max 2.000 [get_ports {sum cout}]

#-----------------------------------------------------------------------
# Input Transition Times
#-----------------------------------------------------------------------

set_input_transition 0.2 [get_ports a]
set_input_transition 0.2 [get_ports b]
set_input_transition 0.2 [get_ports cin]

#-----------------------------------------------------------------------
# Output Load
#-----------------------------------------------------------------------

# Adjust the load value (in pF) based on the expected load of the downstream logic.
set_load 0.1 [get_ports sum]
set_load 0.1 [get_ports cout]

#-----------------------------------------------------------------------
# False Path Constraints (Example)
#-----------------------------------------------------------------------

#If any path is known to be asynchronous or irrelevant for timing, it can be marked as false.  No obvious one here.
#set_false_path -from [get_ports a] -to [get_ports cout]  #Example - check design intent

#-----------------------------------------------------------------------
# Max Delay Constraints (Example)
#-----------------------------------------------------------------------

#If a certain path should never exceed a specific delay.  Unlikely here but possible.
#set_max_delay 4.0 -from [get_ports a] -to [get_ports sum] #Example

#-----------------------------------------------------------------------
# Advanced Constraints
#-----------------------------------------------------------------------

# 1. Clock Uncertainty: Account for clock jitter and wander.
set_clock_uncertainty -setup 0.2 [get_clocks clk_a]
set_clock_uncertainty -hold 0.1 [get_clocks clk_a]

set_clock_uncertainty -setup 0.2 [get_clocks clk_b]
set_clock_uncertainty -hold 0.1 [get_clocks clk_b]

set_clock_uncertainty -setup 0.2 [get_clocks clk_cin]
set_clock_uncertainty -hold 0.1 [get_clocks clk_cin]

# 2. Clock Latency: Specify the insertion delay of the clock network. Adjust based on the clock tree synthesis results.
# Note: This is usually done AFTER clock tree synthesis.  These are just examples.
# set_clock_latency -source -max 1.5 [get_clocks clk_a]
# set_clock_latency -source -min 0.5 [get_clocks clk_a]

# 3. Input/Output Slew Rate Control (for advanced tools):  If supported by the tool flow, constrain the slew rate of input/output signals to further refine timing analysis. This requires more detailed knowledge of the IO standards.  Not included for brevity.

# 4. Operating Conditions: Select the appropriate operating conditions (temperature, voltage) for timing analysis.
set_operating_conditions -max_temperature 85 -min_temperature -40 -process typical -voltage 1.1

# 5. Case Analysis:  If certain input combinations will never occur, use case analysis to remove pessimism from timing analysis.  No obvious cases here, as all combinations of full adder inputs are valid.

#-----------------------------------------------------------------------
# End of SDC file
#-----------------------------------------------------------------------