{% macro date_key(date_column) %}
    cast(strftime({{ date_column }}, '%Y%m%d') as integer)
{% endmacro %}