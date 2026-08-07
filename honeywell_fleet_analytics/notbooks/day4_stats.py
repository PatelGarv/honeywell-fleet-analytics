


import sys
sys.path.append('../scripts')
from snowflake_conn import query_to_df
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.proportion import proportion_confint


print("-><-" * 20)
print("Statstical Validation")
print("-><-" * 20)

# Load Data 

print("\n[1/5] Loading component-level data...")

df = query_to_df("""
SELECT 
    c.component_id,
    c.component_type,
    c.maintenance_protocol,
    COUNT(CASE WHEN t.status = 'CRITICAL' THEN 1 END) as critical_count,
    COUNT(CASE WHEN t.status IN ('WARNING','CRITICAL') THEN 1 END) as any_failure,
    AVG(t.alert_severity_score) as avg_severity,
    MAX(t.alert_severity_score) as max_severity
FROM DBT_GARV_STAGING.STG_COMPONENTS c
LEFT JOIN DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS t ON c.component_id = t.component_id
GROUP BY 1, 2, 3
""")

# Create a balanced failure label
threshold = df['CRITICAL_COUNT'].median()
df['FAILED'] = (df['CRITICAL_COUNT'] >= threshold).astype(int)

print(df['FAILED'].value_counts())

print(df[['COMPONENT_ID','CRITICAL_COUNT','FAILED']].head(20))
print()
print(df['FAILED'].value_counts())
print()
print(df['CRITICAL_COUNT'].describe())

standard = df[df['MAINTENANCE_PROTOCOL'] == 'standard']
predictive = df[df['MAINTENANCE_PROTOCOL'] == 'predictive_v2']

print(f"   Standard group: {len(standard)} components")
print(f"   Predictive_v2 group: {len(predictive)} components")



# T- Test : For avg severity score difference...btw Std_avg_serverity and predictive_avg_serverity


t_stat, p_value = stats.ttest_ind(
    predictive['AVG_SEVERITY'].dropna(),
    standard['AVG_SEVERITY'].dropna(),
    equal_var=False
)

print(f"\n   Standard avg severity:  {standard['AVG_SEVERITY'].mean():.2f}")
print(f"   Predictive avg severity: {predictive['AVG_SEVERITY'].mean():.2f}")
print(f"   Difference: {standard['AVG_SEVERITY'].mean() - predictive['AVG_SEVERITY'].mean():.2f} points")
print(f"   T-statistic: {t_stat:.3f}")
print(f"   P-value: {p_value:.4f}")

if p_value < 0.05:
    print(f"\n SIGNIFICANT (p < 0.05)")
    print(f"   The severity difference is REAL, not a random change.")
else:
    print(f"\n NOT significant (p >= 0.05)")


# Chi-square Test : To check newer Protocol are affecting failure rate or not?

# Build contingency table
contingency = pd.crosstab(df['MAINTENANCE_PROTOCOL'], df['FAILED'])
print(f"\n   Contingency Table (Protocol vs Failed):")
print(contingency)

chi2, p, dof, expected = stats.chi2_contingency(contingency)

std_rate = standard['FAILED'].mean()
pred_rate = predictive['FAILED'].mean()

print(f"\n   Standard failure rate:     {std_rate:.2%}")
print(f"   Predictive_v2 failure rate: {pred_rate:.2%}")
print(f"   Chi-square: {chi2:.3f}")
print(f"   P-value: {p:.4f}")

if p < 0.05:
    print(f"\n   SIGNIFICANT: Protocol DOES affect failure rate.")
else:
    print(f"\n   NOT significant.")





# Confinence Intervals : How precise is our estimation?



std_ci_low, std_ci_high = proportion_confint(
    standard['FAILED'].sum(), len(standard), alpha=0.05, method='wilson'
)
pred_ci_low, pred_ci_high = proportion_confint(
    predictive['FAILED'].sum(), len(predictive), alpha=0.05, method='wilson'
)

print(f"\n   Standard protocol:")
print(f"      Failure rate: {std_rate:.2%}")
print(f"      95% CI: [{std_ci_low:.2%}, {std_ci_high:.2%}]")
print(f"      Meaning: We're 95% sure the TRUE rate is between {std_ci_low:.1%} and {std_ci_high:.1%}")

print(f"\n   Predictive_v2 protocol:")
print(f"      Failure rate: {pred_rate:.2%}")
print(f"      95% CI: [{pred_ci_low:.2%}, {pred_ci_high:.2%}]")
print(f"      Meaning: We're 95% sure the TRUE rate is between {pred_ci_low:.1%} and {pred_ci_high:.1%}")

# Check if intervals overlap
if std_ci_high < pred_ci_low or pred_ci_high < std_ci_low:
    print(f"\n The confidence intervals do NOT overlap.")
    print(f"   This strongly suggests the difference is real.")
else:
    print(f"\n The confidence intervals overlap slightly.")







# Logistic Regression: Predict failure from sensor features


from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

# Prepare features
features = ['AVG_SEVERITY', 'MAX_SEVERITY']
X = df[features].fillna(df[features].median())
y = df['FAILED']

# Encode protocol as number
X = X.copy()
X['protocol'] = (df['MAINTENANCE_PROTOCOL'] == 'predictive_v2').astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(f"\n   Model Performance:")
print(f"   ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")
print(f"   (0.5 = random, 1.0 = perfect, >0.7 = decent)")

print(f"\n   Feature Importance (Coefficients):")
for feat, coef in zip(X.columns, model.coef_[0]):
    direction = "INCREASES" if coef > 0 else "DECREASES"
    print(f"   • {feat}: {coef:+.3f} → {direction} failure probability")




# Plot : Failure Rate with Confidence Intervals

print("\n loading plot for creating failure reate comparison ") 

fig, ax = plt.subplots(figsize=(8, 5))
protocols = ['Standard', 'Predictive_v2']
rates = [std_rate, pred_rate]
errors_low = [std_rate - std_ci_low, pred_rate - pred_ci_low]
errors_high = [std_ci_high - std_rate, pred_ci_high - pred_rate]
errors = [errors_low, errors_high]

bars = ax.bar(protocols, rates, color=['#e74c3c', '#2ecc71'], alpha=0.8, width=0.5)
ax.errorbar(protocols, rates, yerr=errors, fmt='none', color='black', capsize=8, capthick=2)

for bar, rate in zip(bars, rates):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
            f'{rate:.1%}', ha='center', va='bottom', fontsize=12, fontweight='bold')

ax.set_ylabel('Critical Failure Rate')
ax.set_title('A/B Test: Critical Failure Rate by Maintenance Protocol\n(with 95% Confidence Intervals)', 
             fontsize=12, fontweight='bold')
ax.set_ylim(0, max(rates) * 1.4)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('../data/ab_test_failure_rates.png', dpi=150)
print(" Saved: data/ab_test_failure_rates.png")




print(f"""
STATISTICAL VALIDATION (Python: SciPy, Statsmodels, Scikit-learn):

A/B Test — Standard vs Predictive_v2 Maintenance:
• T-Test on severity scores: p = {p_value:.4f} {'(SIGNIFICANT)' if p_value < 0.05 else '(not significant)'}
• Chi-Square on failure rates: p = {p:.4f} {'(SIGNIFICANT)' if p < 0.05 else '(not significant)'}
• Standard failure rate: {std_rate:.1%} [95% CI: {std_ci_low:.1%}, {std_ci_high:.1%}]
• Predictive_v2 failure rate: {pred_rate:.1%} [95% CI: {pred_ci_low:.1%}, {pred_ci_high:.1%}]
• Absolute reduction: {abs(std_rate - pred_rate):.1%}

Logistic Regression:
• ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}
• Top predictors: avg_severity, max_severity, protocol
""")
print("-><-" * 20)
