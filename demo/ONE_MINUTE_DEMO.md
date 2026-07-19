# One-Minute Darbhanga Demo

## Before Starting

- App is warm and the Darbhanga demo snapshot is loaded.
- Maternal emergency is selected.
- Tavily is cached-only unless the canary passed.
- Referral Copilot is off and absent from navigation.

## Script

**0-10 seconds**

Open Medical Desert Planner and select Darbhanga, Bihar. State: "This is planning support based on documentary evidence, not confirmation of current services or a medical desert."

**10-20 seconds**

Show 15 observed records and 0 maternal-emergency policy matches. Point out that the result is low nearby documentary support or insufficient evidence according to assessability, not missing care.

**20-30 seconds**

Switch to emergency surgery and show exactly three matches:

- Darbhanga Medical College
- Paras Global Darbhanga
- R. B. Memorial Hospital

Switch to advanced imaging and show the first two only.

**30-40 seconds**

Open NFHS district context and show `24.9`, `69.9`, and `60.8`. State that these are separate survey estimates and do not alter facility support.

**40-50 seconds**

Open the Verification Queue. Show Lifecare Hospital (Siwan, longitude `84.3447`, PIN `846001`) or Skin Hair Laser Clinic (Purnea, longitude `87.4888`, PIN `846004`). Explain that the PIN join suggests Darbhanga but the city/coordinates conflict, so the record is flagged and excluded from confident aggregation.

**50-60 seconds**

Save and reopen the scenario. Show the immutable snapshot, trace ID, and `update pending` state. Close with: "Every conclusion is cited or explicitly insufficient, and human review changes current results without erasing history."
