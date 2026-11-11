from __future__ import annotations

from path_optimizer.paths import _import_fullcontrol

__all__ = [
    "raise3D_startup_as_steps",
    "raise3D_purge",
    "raise3D_finish",
    "raise3D_layer_change",
]

def raise3D_startup_as_steps(
    extrusion_multiplier: float = 100,
    heatbed_temp: float = 55,
    nozzle_temp_extruder0: float = 215,
    pressure_advance: float = 0.03,
    fan_beginning: int = 0,
    rapid_speed: int = 9000,
) -> list:
    """Raise3D start-up sequence as FullControl steps, without the purge.

    This is the same preamble as :func:`write_raise3D_startCode`, but as step
    objects instead of a G-code string, so it can go at the front of a
    FullControl step list and the design can follow it directly.  It sets the
    extrusion multiplier, heats the bed and nozzle and waits for them, selects
    tool 0, sets pressure advance on both extruders, switches to mm, absolute
    coordinates and absolute extrusion, sets the fan, homes, raises the bed to
    Z0.5 and resets E to zero.

    The purge line is left out.  Add :func:`raise3D_purge` straight after this
    to get one, so it can be moved or dropped without touching the rest.

    Parameters
    ----------
    extrusion_multiplier : float
        Flow percentage for tool 0 (``M221``), where 100 means unchanged.
    heatbed_temp : float
        Bed temperature in °C.  Heating starts first; the wait comes after the
        nozzle is up to temperature, so the two heat at the same time.
    nozzle_temp_extruder0 : float
        Nozzle temperature for tool 0 in °C.  Waits until reached.
    pressure_advance : float
        ``M572`` value, applied to both drives (``D0`` and ``D1``).
    fan_beginning : int
        Part-cooling fan speed at the start, in percent.

    Returns
    -------
    list
        FullControl steps (``ManualGcode``, ``Buildplate``, ``Hotend``, ...),
        in order.  Concatenate them in front of the design steps.
    """
    fc = _import_fullcontrol()
    starting_procedure_steps = []
    starting_procedure_steps.append(fc.ManualGcode(text=f"M221 T0 S{extrusion_multiplier:.2f}; Extrusion multiplier"))
    starting_procedure_steps.append(fc.Buildplate(temp=heatbed_temp, wait=False))
    #starting_procedure_steps.append(fc.Hotend(temp=nozzle_temp_extruder0, wait=True))
    starting_procedure_steps.append(fc.ManualGcode(text=f"M109 T0 S{nozzle_temp_extruder0}; Nozzle heating with tool specification"))
    #TODO tool number addition for m104
    starting_procedure_steps.append(fc.ManualGcode(text="T0; Select Tool 0"))
    starting_procedure_steps.append(fc.Buildplate(temp=heatbed_temp, wait=True))
    starting_procedure_steps.append(fc.ManualGcode(text=f"M572 D0 S{pressure_advance:.2f}; Pressure advance setting"))
    starting_procedure_steps.append(fc.ManualGcode(text=f"M572 D1 S{pressure_advance:.2f}; Pressure advance setting"))
    starting_procedure_steps.append(fc.PrinterCommand(id="units_mm"))  # G21
    starting_procedure_steps.append(fc.PrinterCommand(id="absolute_coords"))  # G90
    starting_procedure_steps.append(fc.Extruder(relative_gcode=False))  # M82
    starting_procedure_steps.append(fc.ManualGcode(text="M107"))
    starting_procedure_steps.append(fc.Fan(speed_percent=fan_beginning))
    starting_procedure_steps.append(fc.ManualGcode(text="G28; Home Axis"))
    starting_procedure_steps.append(fc.ManualGcode(text="G1 Z0.5 F500; Raise bed"))
    starting_procedure_steps.append(fc.ManualGcode(text="G92 E0; Reset extruder position"))
    starting_procedure_steps.append(fc.Printer(travel_speed=rapid_speed))
    return starting_procedure_steps


def raise3D_purge(
    purge_x: float = 60,
    purge_y: float = -2,
    purge_z: float = 0.2,
    purge_length: float = 80,
    purge_feedrate: float = 200,
    purge_length_extruded: float = 12,
    purge_end_height: float = 5,
    z_feedrate: float = 300,
    rapid_speed: float = 9000,
) -> list:
    """Raise3D purge line as FullControl steps.

    Travels to ``(purge_x, purge_y, purge_z)`` and extrudes a straight line in
    +X to prime the nozzle.  Then it lifts to ``purge_end_height`` while
    pushing out a little more filament, so the nozzle leaves the line without
    pulling a string, and resets E to zero so the design starts from a clean
    extruder position.

    Run this after :func:`raise3D_startup_as_steps`.  It assumes the printer is
    already homed, hot, and set to absolute coordinates and absolute extrusion
    (``M82``), all of which that function does.

    .. note::

       This sets FullControl's travel speed to 400 and does not set it back.
       Set ``fc.Printer(travel_speed=...)`` again before the design if it
       needs something different.

    Parameters
    ----------
    purge_x, purge_y : float
        Where the purge line starts, in mm, in printer coordinates.  The
        default ``y = -2`` puts it just in front of the print area so it stays
        clear of the part.
    purge_z : float
        Nozzle height for the purge line, in mm.
    purge_length : float
        Length of the line in +X, in mm.
    purge_feedrate : float
        Feedrate for the line and the lift, in mm/min.
    purge_length_extruded : float
        Absolute E value at the end of the line, i.e. how much filament the
        line uses, in mm.  The lift pushes out another 3 mm on top of this.
    purge_end_height : float
        Z to lift to after the line, in mm.

    Returns
    -------
    list
        FullControl steps, in order.  Concatenate them after the start-up
        steps and before the design.
    """
    fc = _import_fullcontrol()
    purge_end_x = purge_x + purge_length
    purge_end_extrusion = purge_length_extruded + 3
    purge_procedure_steps = []
    purge_procedure_steps.append(fc.Printer(travel_speed=z_feedrate))
    purge_procedure_steps.append(fc.Point(x=purge_x, y=purge_y, z=purge_z))
    purge_procedure_steps.append(fc.ManualGcode(text=f"G1 X{purge_end_x} E{purge_length_extruded} F{purge_feedrate}; Purge line"))
    purge_procedure_steps.append(fc.Point(z=purge_end_height))
    purge_procedure_steps.append(fc.ManualGcode(text=f"G1 E{purge_end_extrusion} F{purge_feedrate}; Purge end hover"))
    purge_procedure_steps.append(fc.ManualGcode(text="G92 E0; Reset extruder position"))
    purge_procedure_steps.append(fc.Printer(travel_speed=rapid_speed))
    purge_procedure_steps.append(fc.ManualGcode(text="M117 Printing..."))
    purge_procedure_steps.append(fc.ManualGcode(text="M1001"))
    purge_procedure_steps.append(fc.ManualGcode(text="M204 T1500"))
    return purge_procedure_steps


def raise3D_finish(
    last_z: float = 200,
    max_z: float = 300,
    acceleration: float = 1000,
    retraction: float = 0.5,
    retraction_feedrate: float = 2400,
    z_lift: float = 4.8,
    z_lift_feedrate: float = 300,
    final_z_lift: float = 0.5,
) -> list:
    """Raise3D end-of-print sequence as FullControl steps.

    Mirrors the end code written by ideaMaker.  It turns the part fan off,
    retracts, lifts the nozzle clear of the part, resets the flow multiplier,
    switches off the nozzle and bed heaters and all fans, does a final
    retract-and-lift while moving away in -Y, homes X (and U), disables the
    motors and returns to absolute coordinates.

    ideaMaker retracts to an absolute E value based on the previous extrusion.
    Here E is reset to zero first (``G92 E0``) and the retract goes to
    ``E-retraction``, so it works whatever E the design ended on.

    Both Z lifts are limited so the nozzle never goes above ``max_z``: the
    first lift goes to ``min(last_z + z_lift, max_z)`` and the final lift is
    cut down to whatever room is left (possibly zero).

    Add this at the end of the FullControl step list, after the design.

    Parameters
    ----------
    last_z : float
        Z height of the last point of the design, in mm.  Needed to work out
        how far the nozzle can be lifted.
    max_z : float
        Highest Z the printer can reach, in mm.  The default of 300 suits the
        Raise3D Pro2 / Pro3; use 240 for the E2.
    acceleration : float
        Print acceleration set at the end (``M204 P``), in mm/s².
    retraction : float
        Filament retracted after the last move, in mm.
    retraction_feedrate : float
        Feedrate for that retraction, in mm/min.
    z_lift : float
        Distance the nozzle is lifted above the last layer, in mm.
    z_lift_feedrate : float
        Feedrate for the lift, in mm/min.
    final_z_lift : float
        Extra relative lift during the last retract-and-move-away, in mm.

    Returns
    -------
    list
        FullControl steps, in order.  Concatenate them after the design steps.

    Raises
    ------
    ValueError
        If ``last_z`` is already above ``max_z``.
    """
    if last_z > max_z:
        raise ValueError(f"last_z ({last_z}) is above the printer's max_z ({max_z}).")
    lift_z = min(last_z + z_lift, max_z)
    final_lift = max(0.0, min(final_z_lift, max_z - lift_z))

    fc = _import_fullcontrol()
    finish_procedure_steps = []
    finish_procedure_steps.append(fc.ManualGcode(text=f"M204 P{acceleration:.2f}; Set acceleration"))
    finish_procedure_steps.append(fc.Fan(speed_percent=0))  # M106 S0
    finish_procedure_steps.append(fc.Extruder(relative_gcode=False))  # M82 + G92 E0
    finish_procedure_steps.append(fc.ManualGcode(text=f"G1 F{retraction_feedrate} E{-retraction}; Retract"))
    finish_procedure_steps.append(fc.ManualGcode(text=f"G0 F{z_lift_feedrate} Z{lift_z:.3f}; Lift nozzle"))
    finish_procedure_steps.append(fc.ManualGcode(text="M221 T0 S100; Reset extrusion multiplier"))
    finish_procedure_steps.append(fc.Extruder(relative_gcode=False))  # M82 + G92 E0
    finish_procedure_steps.append(fc.ManualGcode(text="M1002; End of print"))
    finish_procedure_steps.append(fc.Hotend(temp=0, wait=False, tool=0))  # M104 S0 T0
    finish_procedure_steps.append(fc.ManualGcode(text="M221 T0 S100; Reset extrusion multiplier"))
    finish_procedure_steps.append(fc.Hotend(temp=0, wait=False))  # M104 S0
    finish_procedure_steps.append(fc.Buildplate(temp=0, wait=False))  # M140 S0
    finish_procedure_steps.append(fc.ManualGcode(text="M106 P2 S0; Fan 2 off"))
    finish_procedure_steps.append(fc.ManualGcode(text="M107; Fans off"))
    finish_procedure_steps.append(fc.PrinterCommand(id="relative_coords"))  # G91
    finish_procedure_steps.append(fc.ManualGcode(text="G1 E-1 F300; Retract"))
    finish_procedure_steps.append(fc.ManualGcode(text=f"G1 Z+{final_lift:.3f} E-5 Y-20 F9000.00; Retract, lift and move away"))
    finish_procedure_steps.append(fc.ManualGcode(text="G28 X0 U0; Home X"))
    finish_procedure_steps.append(fc.ManualGcode(text="M84; Disable motors"))
    finish_procedure_steps.append(fc.PrinterCommand(id="absolute_coords"))  # G90
    return finish_procedure_steps


def raise3D_layer_change(
    layer: int,
    z: float,
    layer_height: float,
    next_x: float | None = None,
    next_y: float | None = None,
    max_z: float = 300,
    fan_percent: float = 100,
    aux_fan: int = 0,
    z_feedrate: float = 300,
    rapid_speed: float = 9000,
    acceleration: float = 500,
) -> list:
    """Raise3D layer change as FullControl steps.

    Mirrors the layer change written by ideaMaker: layer comments
    (``;LAYER``, ``;Z``, ``;HEIGHT``), part fan and auxiliary fan on, a slow
    travel up to the new layer height, an optional travel to the first point
    of the layer, and the print acceleration for the layer (``M204``).

    The extruder is switched off for the moves and back on at the end, so the
    next design point after these steps is printed, not travelled to.

    .. note::

       This sets FullControl's travel speed to ``travel_feedrate`` and does
       not set it back.

    Parameters
    ----------
    layer : int
        Layer number, for the ``;LAYER`` comment.
    z : float
        Nozzle height for the new layer, in mm.
    layer_height : float
        Layer thickness, for the ``;HEIGHT`` comment, in mm.
    next_x, next_y : float, optional
        First point of the new layer.  If both are given, the nozzle travels
        there after the Z move; otherwise the travel is left to the design.
    max_z : float
        Highest Z the printer can reach, in mm.
    fan_percent : float
        Part-cooling fan speed for the layer, in percent (``M106 S``).
    aux_fan : int
        Auxiliary fan (``M106 P2``) PWM value, 0-255.
    z_feedrate : float
        Feedrate for the move up to ``z``, in mm/min.
    travel_feedrate : float
        Feedrate for the travel to ``(next_x, next_y)``, in mm/min.
    acceleration : float
        Print acceleration for the layer (``M204 P``), in mm/s².

    Returns
    -------
    list
        FullControl steps, in order.  Insert them between layers.

    Raises
    ------
    ValueError
        If ``z`` is above ``max_z``.
    """
    if z > max_z:
        raise ValueError(f"z ({z}) is above the printer's max_z ({max_z}).")

    fc = _import_fullcontrol()
    layer_change_steps = []
    layer_change_steps.append(fc.GcodeComment(text=f"LAYER:{layer}"))
    layer_change_steps.append(fc.GcodeComment(text=f"Z:{z:.3f}"))
    layer_change_steps.append(fc.GcodeComment(text=f"HEIGHT:{layer_height:.3f}"))
    layer_change_steps.append(fc.Fan(speed_percent=fan_percent))  # M106 S
    layer_change_steps.append(fc.ManualGcode(text=f"M106 P2 S{aux_fan}; Auxiliary fan"))
    layer_change_steps.append(fc.Extruder(on=False))
    layer_change_steps.append(fc.Printer(travel_speed=z_feedrate))
    layer_change_steps.append(fc.Point(z=z))  # G0 F300 Z
    layer_change_steps.append(fc.Printer(travel_speed=rapid_speed))
    if next_x is not None and next_y is not None:
        layer_change_steps.append(fc.Point(x=next_x, y=next_y))  # G0 F9000 X Y
    layer_change_steps.append(fc.ManualGcode(text=f"M204 P{acceleration:.2f}; Set acceleration"))
    layer_change_steps.append(fc.Extruder(on=True))
    return layer_change_steps