import sys
sys.path.append('../scripts')
from snowflake_conn import query_to_df
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load all dbt marts
funnel = query_to_df("SELECT * FROM DBT_GARV_MARTS.MART_DEGRADATION_FUNNEL")
survival = query_to_df("SELECT * FROM DBT_GARV_MARTS.MART_COMPONENT_SURVIVAL")
experiment = query_to_df("SELECT * FROM DBT_GARV_MARTS.MART_MAINTENANCE_EXPERIMENT")
telemetry = query_to_df("SELECT * FROM DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS")

print("Funnel:", funnel.shape)
print("Survival:", survival.shape)
print("Experiment:", experiment.shape)
print("Telemetry:", telemetry.shape)




# Section B for Fleet Health Score (Daily)

fleet_health = query_to_df("""
SELECT 
    DATE(READING_TIMESTAMP) as date,
    COUNT(DISTINCT CASE WHEN STATUS = 'NORMAL' THEN COMPONENT_ID END) * 1.0 / 
        NULLIF(COUNT(DISTINCT COMPONENT_ID), 0) as health_ratio,
    COUNT(DISTINCT CASE WHEN STATUS IN ('WARNING','CRITICAL') THEN AIRCRAFT_ID END) as aircraft_with_alerts,
    AVG(ALERT_SEVERITY_SCORE) as fleet_avg_severity,
    COUNT(DISTINCT COMPONENT_ID) as total_components_monitored
FROM DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS
GROUP BY 1
ORDER BY 1
""")

fleet_health['date'] = pd.to_datetime(fleet_health['DATE'])
fleet_health = fleet_health.sort_values('date')

print(fleet_health.head())
print(f"\nAverage fleet health ratio: {fleet_health['HEALTH_RATIO'].mean():.2%}")





# Section C: Degradation Funnel Visualization

funnel_plot = funnel[['COMPONENT_TYPE', 'NORMAL_COUNT', 'ADVISORY_COUNT', 
'WARNING_COUNT', 'CRITICAL_COUNT']].set_index('COMPONENT_TYPE')

fig, ax = plt.subplots(figsize=(10, 6))
funnel_plot.plot(kind='bar', ax=ax, color=['#2ecc71', '#f39c12', '#e74c3c', '#8e44ad'])
plt.title('Component Degradation Funnel by Type', fontsize=14, fontweight='bold')
plt.xlabel('Component Type')
plt.ylabel('Component Count')
plt.legend(['NORMAL', 'ADVISORY', 'WARNING', 'CRITICAL'])
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('../data/degradation_funnel.png', dpi=150)
plt.show()

print("\nDegradation Transition Rates:")
print(funnel[['COMPONENT_TYPE', 'NORMAL_TO_ADVISORY_RATE', 
'ADVISORY_TO_WARNING_RATE', 'WARNING_TO_CRITICAL_RATE']])







# section D: Component Survival Analytics 

survival_clean = survival[survival['CENSORED'] == 0]

fig, ax = plt.subplots(figsize=(10, 6))
for comp_type in survival_clean['COMPONENT_TYPE'].unique():
    subset = survival_clean[survival_clean['COMPONENT_TYPE'] == comp_type]
    subset = subset.sort_values('MONTHS_TO_FAILURE')
    subset['survival_prob'] = 1 - (subset.reset_index().index + 1) / len(subset)
    ax.plot(subset['MONTHS_TO_FAILURE'], subset['survival_prob'], 
            marker='o', label=comp_type, alpha=0.7)

plt.title('Component Survival Curves', fontsize=14, fontweight='bold')
plt.xlabel('Months to Failure')
plt.ylabel('Survival Probability')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('../data/survival_curves.png', dpi=150)
plt.show()

mtbf = survival_clean.groupby('COMPONENT_TYPE')['DAYS_TO_FAILURE'].agg(['mean', 'median', 'count'])
mtbf.columns = ['MTBF_Days', 'Median_Days', 'Failure_Count']
print("\nMean Time Between Failures (MTBF):")
print(mtbf)







# Section E: Maintenance Cost Simulation 

costs = query_to_df("""
SELECT
    AIRCRAFT_ID,
    SUM(CASE 
        WHEN STATUS = 'ADVISORY' THEN 500
        WHEN STATUS = 'WARNING' THEN 5000
        WHEN STATUS = 'CRITICAL' THEN 25000
        ELSE 0 
    END) as annual_maintenance_cost,
    COUNT(DISTINCT CASE WHEN STATUS = 'CRITICAL' THEN READING_ID END) as unplanned_events,
    COUNT(DISTINCT CASE WHEN STATUS = 'WARNING' THEN READING_ID END) as warning_events,
    AVG(ALERT_SEVERITY_SCORE) as avg_severity
FROM DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS
WHERE DATE(READING_TIMESTAMP) BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY 1
""")

def cost_tier(cost):
    if cost == 0: return 'No Cost'
    elif cost <= 5000: return 'Low'
    elif cost <= 50000: return 'Medium'
    else: return 'High'

costs['COST_TIER'] = costs['ANNUAL_MAINTENANCE_COST'].apply(cost_tier)

print("Maintenance Cost Summary:")
print(costs['COST_TIER'].value_counts())
print(f"\nTotal simulated fleet maintenance cost: ${costs['ANNUAL_MAINTENANCE_COST'].sum():,}")
print(f"Average per aircraft: ${costs['ANNUAL_MAINTENANCE_COST'].mean():,.0f}")

fig, ax = plt.subplots(figsize=(10, 6))
costs.boxplot(column='ANNUAL_MAINTENANCE_COST', by='COST_TIER', ax=ax)
plt.title('Maintenance Cost Distribution by Tier')
plt.suptitle('')
plt.ylabel('Annual Cost ($)')
plt.tight_layout()
plt.savefig('../data/maintenance_costs.png', dpi=150)
plt.show()








# Section F: A/B Test Summary 

ab_summary = experiment.copy()
ab_summary['CRITICAL_RATE'] = ab_summary['CRITICAL_FAILURES'] / ab_summary['TOTAL_COMPONENTS']
ab_summary['WARNING_RATE'] = ab_summary['WARNINGS'] / ab_summary['TOTAL_COMPONENTS']

print("A/B Test: Standard vs Predictive_v2 Maintenance")
print(ab_summary[['MAINTENANCE_PROTOCOL', 'COMPONENT_TYPE', 'CRITICAL_RATE', 
                   'WARNING_RATE', 'AVG_SEVERITY']].round(4))

overall = ab_summary.groupby('MAINTENANCE_PROTOCOL').agg({
    'CRITICAL_FAILURES': 'sum',
    'WARNINGS': 'sum',
    'TOTAL_COMPONENTS': 'sum',
    'AVG_SEVERITY': 'mean'
})
overall['failure_rate'] = overall['CRITICAL_FAILURES'] / overall['TOTAL_COMPONENTS']
print("\nOverall Results:")
print(overall)











fleet_health.to_csv('../data/export_fleet_health.csv', index=False)
funnel.to_csv('../data/export_degradation_funnel.csv', index=False)
survival.to_csv('../data/export_component_survival.csv', index=False)
costs.to_csv('../data/export_maintenance_costs.csv', index=False)
experiment.to_csv('../data/export_maintenance_experiment.csv', index=False)

high_risk = query_to_df("""
SELECT 
    COMPONENT_ID,
    AIRCRAFT_ID,
    COMPONENT_TYPE,
    MODEL,
    OPERATOR,
    MAINTENANCE_PROTOCOL,
    MAX(ALERT_SEVERITY_SCORE) as max_severity,
    AVG(ALERT_SEVERITY_SCORE) as avg_severity,
    COUNT(CASE WHEN STATUS = 'CRITICAL' THEN 1 END) as critical_count,
    COUNT(CASE WHEN STATUS = 'WARNING' THEN 1 END) as warning_count
FROM DBT_GARV_INTERMEDIATE.INT_SENSOR_TRENDS
GROUP BY 1, 2, 3, 4, 5, 6
""")
high_risk.to_csv('../data/export_high_risk_components.csv', index=False)

print("All exports saved to data/ folder")
