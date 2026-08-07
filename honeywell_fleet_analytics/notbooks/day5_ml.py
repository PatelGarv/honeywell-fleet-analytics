import sys
sys.path.append('../scripts')
from snowflake_conn import query_to_df
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')




# 1. LOAD FEATURES (One row per component)

df = query_to_df("""
SELECT 
    c.component_id,
    c.component_type,
    c.maintenance_protocol,
    c.aircraft_id,
    COUNT(t.reading_id) as total_readings,
    COUNT(CASE WHEN t.status = 'CRITICAL' THEN 1 END) as critical_count,
    COUNT(CASE WHEN t.status = 'WARNING' THEN 1 END) as warning_count,
    COUNT(CASE WHEN t.status = 'ADVISORY' THEN 1 END) as advisory_count,
    COUNT(CASE WHEN t.status = 'NORMAL' THEN 1 END) as normal_count,
    AVG(t.alert_severity_score) as avg_severity,
    MAX(t.alert_severity_score) as max_severity,
    MIN(t.alert_severity_score) as min_severity,
    STDDEV(t.alert_severity_score) as std_severity,
    AVG(t.pressure_psi) as avg_pressure,
    AVG(t.temp_c) as avg_temp,
    MAX(t.reading_timestamp) as last_reading,
    DATEDIFF('day', MAX(t.reading_timestamp), CURRENT_DATE()) as recency_days
FROM DBT_GARV_STAGING.STG_COMPONENTS c
LEFT JOIN DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS t ON c.component_id = t.component_id
GROUP BY 1, 2, 3, 4
""")


# Create a balanced target
threshold = df['CRITICAL_COUNT'].median()

df['failed'] = (df['CRITICAL_COUNT'] >= threshold).astype(int)

print(df['failed'].value_counts())

print(f" Loaded {len(df)} components")
print(f" Failures: {df['failed'].sum()} failed, {len(df) - df['failed'].sum()} survived")





# 2. PREPARE FEATURES FOR ML


# Encode categoricals
features_df = pd.get_dummies(df, columns=['COMPONENT_TYPE', 'MAINTENANCE_PROTOCOL', 'AIRCRAFT_ID'], drop_first=True)

# Drop non-feature columns
drop_cols = ['COMPONENT_ID', 'CRITICAL_COUNT', 'WARNING_COUNT', 'ADVISORY_COUNT', 
             'NORMAL_COUNT', 'LAST_READING', 'failed']
X = features_df.drop(columns=[c for c in drop_cols if c in features_df.columns])
y = features_df['failed']

# Fill any NaN
X = X.fillna(X.median())

print(f" Feature matrix: {X.shape[0]} rows x {X.shape[1]} columns")




# 3. TRAIN / TEST SPLIT

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

print(f" Train: {len(X_train)} | Test: {len(X_test)}")





# 4. TRAIN 3 MODELS

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, classification_report

models = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
    'XGBoost': XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)
}

results = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    results[name] = {'model': model, 'auc': auc, 'proba': y_proba}
    print(f" {name}: ROC-AUC = {auc:.3f}")

# Best model
best_name = max(results, key=lambda k: results[k]['auc'])
print(f"\n Best model: {best_name} ({results[best_name]['auc']:.3f})")






# 5. FEATURE IMPORTANCE (Random Forest)

rf_model = results['Random Forest']['model']
importances = pd.Series(rf_model.feature_importances_, index=X.columns)
top_features = importances.nlargest(10)

plt.figure(figsize=(8, 5))
top_features.plot(kind='barh', color='#3498db')
plt.title('Top 10 Feature Importances (Random Forest)', fontweight='bold')
plt.xlabel('Importance')
plt.tight_layout()
plt.savefig('../data/feature_importance_rf.png', dpi=150)
print(" Saved: data/feature_importance_rf.png")





# 6. SHAP EXPLAINABILITY (XGBoost)

import shap

xgb_model = results['XGBoost']['model']
explainer = shap.TreeExplainer(xgb_model)
shap_values = explainer.shap_values(X_test)

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.title('SHAP Feature Importance (XGBoost)', fontweight='bold')
plt.tight_layout()
plt.savefig('../data/shap_summary.png', dpi=150)
print(" Saved: data/shap_summary.png")

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, show=False)
plt.title('SHAP Impact on Model Output', fontweight='bold')
plt.tight_layout()
plt.savefig('../data/shap_beeswarm.png', dpi=150)
print(" Saved: data/shap_beeswarm.png")




# 7. TIME SERIES FORECASTING (Prophet)

from prophet import Prophet

ts_df = query_to_df("""
SELECT 
    DATE(reading_timestamp) as ds,
    COUNT(CASE WHEN status = 'CRITICAL' THEN 1 END) as y
FROM DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS
GROUP BY 1
ORDER BY 1
""")

print(ts_df.columns)

ts_df = ts_df.rename(columns={
    'DS': 'ds',
    'Y': 'y'
})

ts_df['ds'] = pd.to_datetime(ts_df['ds'])



m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
m.fit(ts_df)

future = m.make_future_dataframe(periods=90)
forecast = m.predict(future)

fig1 = m.plot(forecast)
plt.title('Critical Events Forecast (Next 90 Days)', fontweight='bold')
plt.xlabel('Date')
plt.ylabel('Predicted Critical Events')
plt.tight_layout()
plt.savefig('../data/prophet_forecast.png', dpi=150)
print(" Saved: data/prophet_forecast.png")

fig2 = m.plot_components(forecast)
plt.tight_layout()
plt.savefig('../data/prophet_components.png', dpi=150)
print(" Saved: data/prophet_components.png")




print(f"""
FILES GENERATED:
 data/feature_importance_rf.png
 data/shap_summary.png
 data/shap_beeswarm.png
 data/prophet_forecast.png
 data/prophet_components.png

RESUME BULLET:
"Built ensemble ML pipeline (Logistic Regression, Random Forest, XGBoost) 
predicting component failure with {results[best_name]['auc']:.3f} ROC-AUC Factor. Applied SHAP explainability 
to identify top failure drivers. Forecasted critical event trends 90 days 
ahead using Prophet time series model."
""")










