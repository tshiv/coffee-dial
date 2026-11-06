"""Grinder translation: one dial-in move is at least one physical step."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.grind import microns_to_setting, one_step_micron_delta  # noqa: E402
from equipment.loader import get_grinder  # noqa: E402

ODE1 = get_grinder("fellow_ode_gen1")      # 100 microns per setting
COMANDANTE = get_grinder("comandante_c40")  # clicks, finer than one dial-in step


def test_coarser_on_an_ode_gen1_reaches_the_next_setting():
    start = microns_to_setting(ODE1, 730)
    delta = one_step_micron_delta(ODE1, 730, +1, 30)
    assert microns_to_setting(ODE1, 730 + delta) == start + 1


def test_finer_on_an_ode_gen1_reaches_the_previous_setting():
    start = microns_to_setting(ODE1, 730)
    delta = one_step_micron_delta(ODE1, 730, -1, 30)
    assert delta < 0
    assert microns_to_setting(ODE1, 730 + delta) == start - 1


def test_a_fine_grained_grinder_keeps_the_minimum_step():
    assert one_step_micron_delta(COMANDANTE, 700, +1, 30) == 30


def test_at_the_end_stop_it_falls_back_to_the_minimum():
    assert one_step_micron_delta(ODE1, 5000, +1, 30) == 30
    assert one_step_micron_delta(ODE1, 0, -1, 30) == -30
