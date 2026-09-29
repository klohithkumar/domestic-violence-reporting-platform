from classifier import analyze_report


report = """
My husband hit me and constantly threatens me.
He also controls my money and does not allow me
to meet my family.
"""

result = analyze_report(report)

print("\n===== SAFEVOICE AI ANALYSIS =====\n")

for category, data in result.items():

    if data["detected"]:
        print(
            f"{category}: DETECTED "
            f"({data['confidence']}% confidence)"
        )
    else:
        print(
            f"{category}: NOT DETECTED "
            f"({data['confidence']}% confidence)"
        )

print("\n=================================")