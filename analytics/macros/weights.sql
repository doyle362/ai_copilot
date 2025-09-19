{% macro recency_weight(date_col, half_life_days=none) %}
  {% set half_life = half_life_days or env_var('DBT_WEIGHT_HALFLIFE_DAYS', '14') %}
  POWER(0.5, GREATEST(0, DATE_PART('day', CURRENT_DATE - {{ date_col }})) / {{ half_life }}::numeric)
{% endmacro %}