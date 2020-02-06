# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 12:17:18 2019

@author: Ian
"""
# analysis:ignore

import visa
import csv
from time import sleep

from PyQt5.QtWidgets import QInputDialog


class LaserOutOfRangeError(BaseException):
    pass


class CompexLaser:

    def __init__(self, laser_id, visa_backend='@ni'):
        # Create a visa resource manager (Will default to using NI Visa, but
        # you can pass other options like '@py' for the fully python VISA or
        # '@sim' for a simulated backend that connects to dummy instruments)
        self.resManager = visa.ResourceManager(visa_backend)
        self.laserCodes = {}
        with open('Laser_Codes.txt', 'rt') as csv_file:
            for row in csv.reader(csv_file, delimiter='\t'):
                self.laserCodes[row[0]] = row[1:]

        # Setup Class variables
        self.op_delay = 0.01  # Delay for back to back serial ops
        self.trigger_src = self.rd_trigger()


        try:
            self.laser = self.resManager.open_resource(laser_id,
                                                       write_termination='\r',
                                                       read_termination='\r')
        except NameError:
            print(self.resManager.list_resources())
            print("Could not connect to laser, check for instrument name \
                  changes and make sure that the laser is plugged in. Note: \
                  the available resource names are printed above.")

    # Disconnect from the laser gracefully
    def disconnect(self):
        self.laser.close()

    # Pass through methods for laser read, write, query through PyVisa

    def write(self, command):
        self.laser.write(command)

    def read(self):
        return self.laser.read()

    def query(self, command):
        return self.laser.query(command)

# =============================================================================
#     Operations Methods
# =============================================================================

    def off(self):
        # Stops laser operation
        self.laser.write('OPMODE=OFF')

    def on(self):
        # Starts laser operation using set parameters, and a start delay of
        # 4.1s, this start delay allows the user to interrupt startup with the
        # off command.
        self.laser.write('OPMODE=ON')

    def energy_cal(self):
        # Runs the laser's built in energy calibration method, will prompt for
        # a value measured with an external energy meter, and have a cancel
        # FIXME: Needs GUI Element work to allow for ext. energy reading input
        self.laser.write("OPMODE=ENERGY CAL")
        rdmode = self.laser.rd_opmode()
        while rdmode != "OFF:7" and rdmode != "ENERGY CAL CONT":
            rdmode = self.laser.rd_opmode()
            sleep(0.2)
        if rdmode == "OFF:7":
            QInputDialog.getInt(self)

    def flush_line(self, line_name):
        # Flushes(evacuates) the supplied line values can be
        # RARE, HALOGEN, BUFFER, or INERT
        valid_line_names = ['RARE', 'HALOGEN', 'INERT']
        if line_name.upper() in valid_line_names:
            self.laser.write('OPMODE=FLUSH %s LINE' % line_name.upper())
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid line value supplied, command not sent')

    def flush_tube(self):
        # Flushes(evacuates) the laser tube to allow for optics maintenance
        # FIXME: Needs a GUI element to complete the flush as there will be 2x
        # OPMODE=CONT inputs required
        self.laser.write('OPMODE=FLUSHING')

    def halogen_inject(self):
        # Laser performs a halogen injection after a 3 minute waiting period
        # ONLY USED IF WE HAVE CHANGED GAS SOURCES AWAY FROM A PREMIX
        self.laser.write('OPMODE=HI')

    def disable_low_light(self):
        # Disables the low light warning function. Low light function stops
        # laser operation if more than 30% of pulses within 10s are misses.
        self.laser.write('OPMODE=LL OFF')

    def fill_manual_inert(self):
        # Opens the inert valve for 10s to fill the laser tube with inert gas
        # note that this command will only be accepted if the laser is not
        # operating and the tube pressure is less than 3800 mbar.
        self.laser.write('OPMODE=MANUAL FILL INERT')

    def fill_new(self):
        # Begins the new fill procedure for the laser tube. No leak test unless
        # using a halogen source
        self.laser.write('OPMODE=NEW FILL')

    def fill_passivation(self):
        # Starts the passivation fill procedure.
        self.laser.write('OPMODE=PASSIVATION FILL')

    def fill_transport(self):
        # Starts a transport fill, which sets the tube up for safe transport.
        self.laser.write('OPMODE=TRANSPORT FILL')

    def partial_gas_replacement(self):
        # Performs a partial gas replacement, only available when using a
        # halogen source.
        self.laser.write('OPMODE=PGR')

    def purge_line(self, line_name):
        # Purges the selected line (flushes/evacuates and fills with inert).
        self.laser.write('OPMODE=PURGE %s LINE' % line_name.upper())

    def purge_tube(self):
        # Purges the laser tube (flushes/evacuates and fills with inert).
        self.laser.write('OPMODE=PURGE RESERVOIR')

    def skip_warmup(self):
        # Sends command to override warmup and allow laser operation.
        self.laser.write('OPMODE=SKIP')

# =============================================================================
#     Parameter Methods: Used to Set Operations Values
# =============================================================================

    def set_buffer_press(self, mbar):  # Takes an int
        # Sets the partial pressure of gas connected to buffer line
        self.laser.write('BUFFER=%s' % mbar)

    def set_halogen_filter_cap(self, cap):
        # Provides a value for the halogen source capacity as a percentage,
        # 0 <= cap <= 120, this function also runs the set command.
        self.laser.write('CAP.SET=%s' % cap)
        self.laser.write('OPMODE=CAPACITY RESET')

    def set_charge_on_demand(self, is_charge_on_demand):
        # Sets the charge on demand mode for the laser. Note that if COD is
        # set as on, the laser will not accept reprates over 50Hz.
        if is_charge_on_demand is True:
            self.laser.write('COD=ON')
        elif is_charge_on_demand is False:
            self.laser.write('COD=OFF')
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Tried to set invalid value, command not sent')

    def reset_counter(self):
        # Resets the user counter on the laser; Only available when the
        # laser is in off mode.
        self.laser.write('COUNTER=RESET')

    def set_counts(self, counts):
        # Sets a countdown value, this switches the laser to external
        # triggering mode, and allows the laser to run until the remaining
        # counts reduces to 0. Can set 0 <= counts <= 65535.
        self.laser.write('COUNTS=%s' % counts)

    def set_energy(self, mj):
        # In energy constant mode, this sets the target energy value.
        # Setting this value to 0 will reset the laser to the default
        # energy value as defined in the gas menu. Finally, this command
        # is used to set the energy value during energy calibration
        self.laser.write('EGY=%s' % mj)

    def set_energy_range(self, pct):
        # Allows setting the limits for energy setting by percentage of
        # the factory limits. Range of 1 to 100.
        self.laser.write('EGY RANGE=%s' % pct)

    def set_pulse_averaging(self, sample_pop):
        # Sets the number of pulses the laser will used to calculate an
        # average beam energy. If it is out of range this input will be
        # ignored. Valid values: 0, 1, 2, 4, 8, 16.
        valid_sample_pop = [0, 1, 2, 4, 8, 16]
        if sample_pop in valid_sample_pop:
            self.laser.write('FILTER=%s' % sample_pop)
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid averaging number, command not sent')

    def reset_filter_contamination(self):
        # Resets the halogen filter capacity value in percent.
        self.laser.write('FILTER CONTAMINATION=RESET')

    def set_gas_mode(self, mode):
        # Changes the laser between single gas and premix operating modes
        valid_gas_modes = ['SINGLE GASES', 'PREMIX']
        if mode.upper() in valid_gas_modes:
            self.laser.write('GASMODE=%s' % mode)
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Tried to set invalid gas mode, command not sent')

    def set_halogen_press(self, mbar):
        # Sets the partial pressure of gas connected to halogen line
        self.laser.write('HALOGEN=%s' % mbar)

    def set_hv(self, hv):
        # Sets the voltage in HV constant mode
        if self.laser.query('MODE?') == 'HV':
            self.laser.write('HV=%s' % hv)
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Laser not in HV constant mode, command not sent')

    # FIXME: This would be a really useful function as we could set the energy
    # from the programs then let the laser figure out the HV value
    # NOT FUNCTIONAL RIGHT NOW
    def set_hv_energy(self, energy):
        pass
#        self.on()
#        self.readTimer = QTimer(1000 / int(self.rd_reprate()))
#        self.QTimer.timeout.connect(self.rd_energy)

    def set_inert_press(self, mbar):
        # Sets the partial pressure of gas connected to inert line
        self.laser.write('INERT=%s' % mbar)

    def set_menu(self, menu_num):
        # Sets the gas menu by number, probably shouldn't allow direct access
        # to this through the GUI, unless you are going to add a dropdown.
        if 1 <= menu_num <= 6:
            self.laser.write('MENU=%s' % menu_num)
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid menu number supplied, command not sent')

    def reset_menu(self):
        # Resets the menu to the factory defaults
        self.laser.write('MENU=RESET')

    def set_mode(self, mode):
        # Sets the laser operating mode
        valid_modes = ['HV', 'EGY PGR', 'EGY NGR']
        if mode.upper() in valid_modes:
            self.laser.write('MODE=%s' % mode.upper())
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid operating mode supplied, command not sent')

    def set_rare_press(self, mbar):
        # Sets the partial pressure of gas connected to rare line
        self.laser.write('INERT=%s' % mbar)

    def set_reprate(self, hz):
        # Sets the reprate for the laser
        self.laser.write('REPRATE=%s' % hz)

    def set_roomtemp_hilow(self, rt):
        # Only for use with an HCl source as the source reaction is very temp
        # sensitive. Can be set to high (above 22C) or low (below 22C).
        valid_rt = ['HIGH', 'LOW']
        if rt.upper() in valid_rt:
            self.laser.write('ROOMTEMP=%s' % rt.upper())
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid value supplied, remember that roomtemp is a \
                      High or Low value, command not sent')

    def set_timeout(self, timeout):
        if timeout is True:
            self.laser.write('TIMEOUT=ON')
        elif timeout is False:
            self.laser.write('TIMEOUT=OFF')
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid timeout value (should be boolean), \
                      command not sent')

    def set_trigger(self, trigger):
        valid_trigger = ['INT', 'EXT']
        if trigger.upper() in valid_trigger:
            self.laser.write('TRIGGER=%s' % trigger.upper())
            sleep(self.op_delay)
            self.rd_trigger()
        else:
            try:
                raise LaserOutOfRangeError()
            except LaserOutOfRangeError:
                print('Invalid trigger mode supplied, command not sent')

# =============================================================================
#     Polling Methods: Read data and status from the laser.
# =============================================================================

    def rd_accumulator(self):
        # Provides the current pressure in the accumulator if there is a
        # halogen source installed. Will return 0 if there is no halogen
        # source installed.
        return self.laser.query('ACCU?')

    def rd_buffer_press(self):
        # Reads the partial pressure of the buffer gas in mbar
        return self.laser.query('BUFFER?')

    def rd_halogen_source_capacity(self):
        # Reads the remaining halogen source capacity.
        return self.laser.query('CAP.LEFT?')

    def rd_charge_on_demand(self):
        # Reads the charge on demand delay in microseconds.
        # Note: This value is soley determined by laser model.
        return self.laser.query('COD?')

    def rd_counter(self):
        # Reads the current number of pulses accumulated since the last
        # user counter reset
        return self.laser.query('COUNTER?')

    def rd_counts(self):
        # Reads the initial value of the countdown counter. Does
        # not return the number of pulses remaining.
        return self.laser.query('COUNTS?')

    def rd_energy(self):
        # Depending on operating mode: 1) Laser OFF: returns the preset/target
        # energy setting 2) Laser ON: displays the measured beam energy, if
        # polled again between trigger pulses, will return 0 3) During ENERGY
        # CAL: reads the momentary monitor reading (unitless)
        return self.laser.query('EGY?')

    def rd_energy_setting(self):
        # Reads the preset/target energy value for energy constant mode.
        return self.laser.query('EGY SET?')

    def rd_energy_range(self):
        # Reads the energy tolerance range in percent.
        return self.laser.query('EGY RANGE?')

    def rd_pulse_averaging(self):
        # Reads the number of pulses being used to calculate a mean value
        # for the beam energy. A reading of 0 means the value has been set
        # automatically, based on the reprate.
        return self.laser.query('FILTER?')

    def rd_filter_contamination(self):
        # Reads the capacity of the halogen filter in percent
        return self.laser.query('FILTER CONTAMINATION?')

    def rd_gas_mode(self):
        # Reads the current gas mode setting.
        return self.laser.query('GASMODE?')

    def rd_halogen_press(self):
        # Reads the current partial pressure of the halogen gas in mbar.
        return self.laser.query('HALOGEN?')

    def rd_hv(self):
        # Reads the charging voltage in HV mode.
        return self.laser.query('HV?')

    def rd_inert_press(self):
        # Reads the current partial pressure of the inert gas.
        return self.laser.query('INERT?')

    def rd_interlock(self):
        # Reads a comma separated list of activated interlocks. Returns NONE
        # if no interlocks are active.
        # FIXME: Figure out of the Estop is working and why it doesnt seem
        # to throw an interlock
        return self.laser.query('INTERLOCK?')

    def rd_leak_rate(self):
        # For a fluorine source, reads the leak rate of the tube as measured
        # during the new fill procedure. Units of [mbar/2min]
        return self.laser.query('LEAKRATE?')

    def rd_menu(self):
        # Reads the current gas menu number, wavelength, and gas mixture as a
        # a tuple.
        return str.split(self.laser.query('MENU?'), ' ')

    def rd_mode(self):
        # Reads the current laser running mode: HV, EGY PGR, or EGY NGR.
        return self.laser.query('MODE?')

    def rd_opmode(self):
        # Reads the laser opmode state. This value can be parsed to give
        # insight into error states, operation health, etc.
        # FIXME: Should probably set up a parser so that any error
        # states are more readable
        return self.laser.query('OPMODE?')

    def rd_is_power_stabilized(self):
        # Provides a boolean value for power stabilization state.
        if self.laser.query('POWER STABILIZATION ACHIEVED?') == 'YES':
            return True
        return False

    def rd_tube_press(self):
        # Reads the current tube pressure in mbar.
        return self.laser.query('PRESSURE?')

    def rd_pulse_diff(self):
        # Returns the delta of trigger pulses to pulses received by the
        # energy monitor.
        # dp = (# of ext trigger pulses) - (# of pulses measured)
        # FIXME: USE THIS AS A CHECK AFTER DEP PROGRAM RUNS TO MAKE SURE THAT
        # WE ARE GETTING THE CORRECT NUMBER OF PULSES.
        return self.laser.query('PULSE DIFF?')

    def rd_rare_press(self):
        # Reads the partial pressure of the Rare in mbar.
        return self.laser.query('RARE?')

    def rd_reprate(self):
        # Reads the current reprate status.
        return self.laser.query('REPRATE?')

    def rd_roomtemp_hilow(self):
        # Only with a halogen source: Room temp value (can be High or Low), if
        # no halogen source, returns high.
        return self.laser.query('ROOMTEMP?')

    def rd_f_source_temp(self):
        # Reads the temperature in fluorine source, returns 0 if there is no
        # fluorine source is attached.
        return self.laser.query('TEMP?')

    def rd_is_timeout(self):
        # Returns a boolean for if timeout is enabled.
        if self.laser.query('TIMEOUT?') == 'ON':
            return True
        return False

    def rd_total_counter(self):
        # Reads the total counter number of pulses for the laser. Note this
        # value cannot be reset and is for the lifetime of the laser cabinet.
        return self.laser.query('TOTALCOUNTER?')

    def rd_trigger(self):
        # Reads the current laser triggering mode. Returns: INT or EXT.
        self.trigger_src = self.laser.query('TRIGGER?')
        return self.trigger_src

    def rd_laser_model(self):
        # Reads the laser model.
        return self.laser.query('TYPE OF LASER?')

    def rd_version(self):
        # Reads the current laser software version
        return self.laser.query('VERSION?')

    def interpret_opmode(self):
        current_opmode = self.rd_opmode()
        return current_opmode, self.laserCodes[current_opmode]
