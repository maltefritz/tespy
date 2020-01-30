# -*- coding: utf-8

from nose.tools import eq_

from tespy.components.basics import sink, source
from tespy.components.combustion import (combustion_chamber, combustion_engine)
from tespy.connections import connection, bus
from tespy.networks.networks import network

import numpy as np
import shutil


class component_tests:

    def setup(self):

        self.nw = network(['H2O', 'N2', 'O2', 'Ar', 'CO2', 'CH4'],
                          T_unit='C', p_unit='bar', v_unit='m3 / s')
        self.fuel = source('fuel')
        self.air = source('ambient air')
        self.fg = sink('flue gas')

    def setup_combustion_chamber_network(self, instance):

        self.c1 = connection(self.air, 'out1', instance, 'in1')
        self.c2 = connection(self.fuel, 'out1', instance, 'in2')
        self.c3 = connection(instance, 'out1', self.fg, 'in1')
        self.nw.add_conns(self.c1, self.c2, self.c3)

    def setup_combustion_engine_network(self, instance):

        self.cw1_in = source('cooling water 1 source')
        self.cw2_in = source('cooling water 2 source')
        self.cw1_out = sink('cooling water 1 sink')
        self.cw2_out = sink('cooling water 2 sink')

        self.c1 = connection(self.air, 'out1', instance, 'in3')
        self.c2 = connection(self.fuel, 'out1', instance, 'in4')
        self.c3 = connection(instance, 'out3', self.fg, 'in1')
        self.c4 = connection(self.cw1_in, 'out1', instance, 'in1')
        self.c5 = connection(self.cw2_in, 'out1', instance, 'in2')
        self.c6 = connection(instance, 'out1', self.cw1_out, 'in1')
        self.c7 = connection(instance, 'out2', self.cw2_out, 'in1')
        self.nw.add_conns(self.c1, self.c2, self.c3, self.c4, self.c5, self.c6,
                          self.c7)

    def test_combustion_chamber(self):
        """
        Test component properties of combustion chamber.
        """
        instance = combustion_chamber('combustion chamber')
        self.setup_combustion_chamber_network(instance)

        # connection parameter specification
        air = {'N2': 0.7556, 'O2': 0.2315, 'Ar': 0.0129, 'H2O': 0, 'CO2': 0,
               'CH4': 0}
        fuel = {'N2': 0, 'O2': 0, 'Ar': 0, 'H2O': 0, 'CO2': 0.04, 'CH4': 0.96}
        self.c1.set_attr(fluid=air, p=1, T=30)
        self.c2.set_attr(fluid=fuel, T=30)
        self.c3.set_attr(T=1200)

        # test specified bus value on combustion_chamber (must be equal to ti)
        b = bus('thermal input', P=1e6)
        b.add_comps({'c': instance})
        self.nw.add_busses(b)
        self.nw.solve('design')
        msg = ('Value of thermal input must be ' + str(b.P.val) + ', is ' +
               str(instance.ti.val) + '.')
        eq_(round(b.P.val, 1), round(instance.ti.val, 1), msg)
        b.set_attr(P=np.nan)

        # test specified thermal input for combustion_chamber
        instance.set_attr(ti=1e6)
        self.nw.solve('design')
        ti = (self.c2.m.val_SI * self.c2.fluid.val['CH4'] *
              instance.fuels['CH4']['LHV'])
        msg = ('Value of thermal input must be ' + str(instance.ti.val) +
               ', is ' + str(ti) + '.')
        eq_(round(ti, 1), round(instance.ti.val, 1), msg)

        # test specified lamb for combustion_chamber
        self.c3.set_attr(T=np.nan)
        instance.set_attr(lamb=1)
        self.nw.solve('design')
        msg = ('Value of oxygen in flue gas must be 0.0, is ' +
               str(round(self.c3.fluid.val['O2'], 4)) + '.')
        eq_(0.0, round(self.c3.fluid.val['O2'], 4), msg)

    def test_combustion_engine(self):
        """
        Test component properties of combustion engine.
        """
        instance = combustion_engine('combustion engine')
        self.setup_combustion_engine_network(instance)

        air = {'N2': 0.7556, 'O2': 0.2315, 'Ar': 0.0129, 'H2O': 0, 'CO2': 0,
               'CH4': 0}
        fuel = {'N2': 0, 'O2': 0, 'Ar': 0, 'H2O': 0, 'CO2': 0.04, 'CH4': 0.96}
        water1 = {'N2': 0, 'O2': 0, 'Ar': 0, 'H2O': 1, 'CO2': 0, 'CH4': 0}
        water2 = {'N2': 0, 'O2': 0, 'Ar': 0, 'H2O': 1, 'CO2': 0, 'CH4': 0}

        # connection parametrisation
        instance.set_attr(pr1=0.99, pr2=0.99, lamb=1.0,
                          design=['pr1', 'pr2'], offdesign=['zeta1', 'zeta2'])
        self.c1.set_attr(p=5, T=30, fluid=air)
        self.c2.set_attr(T=30, fluid=fuel)
        self.c4.set_attr(p=3, T=60, m=50, fluid=water1)
        self.c5.set_attr(p=3, T=80, m=50, fluid=water2)

        # create busses
        TI = bus('thermal input')
        Q1 = bus('heat output 1')
        Q2 = bus('heat output 2')
        Q = bus('heat output')
        Qloss = bus('thermal heat loss')

        TI.add_comps({'c': instance, 'p': 'TI'})
        Q1.add_comps({'c': instance, 'p': 'Q1'})
        Q2.add_comps({'c': instance, 'p': 'Q2'})
        Q.add_comps({'c': instance, 'p': 'Q'})
        Qloss.add_comps({'c': instance, 'p': 'Qloss'})

        self.nw.add_busses(TI, Q1, Q2, Q, Qloss)

        # test specified thermal input bus value
        ti = 1e6
        TI.set_attr(P=ti)
        self.nw.solve('design')
        self.nw.save('tmp')
        # calculate in offdesign mode
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        msg = ('Value of thermal input must be ' + str(TI.P.val) + ', is ' +
               str(instance.ti.val) + '.')
        eq_(round(TI.P.val, 1), round(instance.ti.val, 1), msg)

        # test specified thermal input in component
        TI.set_attr(P=np.nan)
        instance.set_attr(ti=ti)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        msg = ('Value of thermal input must be ' + str(ti) + ', is ' +
               str(instance.ti.val) + '.')
        eq_(round(ti, 1), round(instance.ti.val, 1), msg)
        instance.set_attr(ti=np.nan)

        # test specified heat output 1 bus value
        Q1.set_attr(P=instance.Q1.val)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        # heat output is at design point value, thermal input must therefore
        # not have changed
        msg = ('Value of thermal input must be ' + str(ti) + ', is ' +
               str(instance.ti.val) + '.')
        eq_(round(ti, 1), round(instance.ti.val, 1), msg)

        # calculate heat output over cooling loop
        heat1 = self.c4.m.val_SI * (self.c6.h.val_SI - self.c4.h.val_SI)
        msg = ('Value of thermal input must be ' + str(heat1) + ', is ' +
               str(instance.Q1.val) + '.')
        eq_(round(heat1, 1), round(instance.Q1.val, 1), msg)
        Q1.set_attr(P=np.nan)

        # test specified heat output 2 bus value
        Q2.set_attr(P=1.2 * instance.Q2.val)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')

        # calculate heat output over cooling loop, due to characteristic
        # function Q1 is equal to Q2 for this combustion engine
        heat1 = self.c4.m.val_SI * (self.c6.h.val_SI - self.c4.h.val_SI)
        msg = ('Value of heat output 2 must be ' + str(heat1) + ', is ' +
               str(instance.Q2.val) + '.')
        eq_(round(heat1, 1), round(instance.Q2.val, 1), msg)

        # test specified heat output 2 in component
        Q2.set_attr(P=np.nan)
        instance.set_attr(Q2=heat1)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        heat1 = self.c4.m.val_SI * (self.c6.h.val_SI - self.c4.h.val_SI)
        msg = ('Value of heat output 2 must be ' + str(heat1) + ', is ' +
               str(instance.Q2.val) + '.')
        eq_(round(heat1, 1), round(instance.Q2.val, 1), msg)

        # test total heat output bus value
        instance.set_attr(Q2=np.nan)
        Q.set_attr(P=1.5 * instance.Q1.val)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        heat = (self.c4.m.val_SI * (self.c6.h.val_SI - self.c4.h.val_SI) +
                self.c5.m.val_SI * (self.c7.h.val_SI - self.c5.h.val_SI))
        msg = ('Value of total heat output must be ' + str(Q.P.val) +
               ', is ' + str(heat) + '.')
        eq_(round(Q.P.val, 1), round(heat, 1), msg)

        # test specified heat loss bus value
        Q.set_attr(P=np.nan)
        Qloss.set_attr(P=1e5)
        self.nw.solve('offdesign', init_path='tmp', design_path='tmp')
        msg = ('Value of heat loss must be ' + str(Qloss.P.val) + ', is ' +
               str(instance.Qloss.val) + '.')
        eq_(round(Qloss.P.val, 1), round(instance.Qloss.val, 1), msg)
        shutil.rmtree('./tmp', ignore_errors=True)
