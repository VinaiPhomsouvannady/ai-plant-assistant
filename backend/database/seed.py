from backend.models import DocumentCreate

SEED_DOCUMENTS = [
    DocumentCreate(
        title="Centrifugal Pump P-204: Low Discharge Pressure",
        equipment="Centrifugal pump",
        source="Pump maintenance procedure 04-22",
        content="If discharge pressure is low, verify suction valve position and check the suction strainer for blockage. Confirm the pump is rotating in the correct direction and inspect the mechanical seal for leakage. Do not operate below minimum flow. If the strainer differential pressure is high, isolate and clean it under the lockout/tagout procedure before restarting.",
    ),
    DocumentCreate(
        title="Heat Exchanger E-101: Outlet Temperature Drift",
        equipment="Heat exchanger",
        source="Utilities operating standard 11-08",
        content="For an outlet temperature drift, compare inlet temperatures and flow rates against the operating log. Check the control valve position and verify the temperature sensor calibration. Fouling on the process side can reduce heat transfer. Escalate if outlet temperature exceeds the trip limit or if pressure drop rises unexpectedly.",
    ),
    DocumentCreate(
        title="Compressor K-301: High Vibration Response",
        equipment="Compressor",
        source="Rotating equipment alarm response 07-14",
        content="A high vibration alarm requires confirmation from the local indicator and control-room trend. Check bearing temperature, lube-oil pressure, and recent process changes. Keep clear of the coupling and rotating equipment. If vibration continues to rise, reduce load and notify the shift supervisor for a controlled shutdown assessment.",
    ),
]
