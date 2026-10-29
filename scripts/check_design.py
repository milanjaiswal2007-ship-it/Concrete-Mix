html = open("app/templates/design.html", encoding="utf-8").read()
ids = [
    "resultsPlaceholder", "resultsContainer", "conventionalResults", "specialResults", "errorBox", "errorDetails",
    "specialTypeTitle", "specialBaseId", "specialDisclaimerText", "specialVerificationBadge", "specialStrengthRange",
    "specialQuantitiesTable", "specialCuring", "specialAir", "specialWorkability", "specialParamExtra",
    "specialChecksList", "specialExpectedProps", "specialSourcesList", "specialSimilarList",
    "resTargetSummary", "resRatio", "resCement", "resWater", "resWcVal", "resFA", "resCA", "resScmBreakdown",
    "resSpMass", "resFieldAdj", "auditTableBody", "resStepsContainer", "similarExamplesList"
]
missing = [i for i in ids if f'id="{i}"' not in html]
print("MISSING IDs:", missing)
