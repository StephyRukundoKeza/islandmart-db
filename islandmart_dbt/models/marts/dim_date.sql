with days as (
    select cast(range as date) as full_date
    from range(date '2026-01-01', date '2027-01-01', interval 1 day)
),

holidays as (
    select
        cast(holiday_date as date)      as holiday_date,
        string_agg(holiday_name, ' / ') as holiday_name
    from {{ ref('mauritius_public_holidays_2026') }}
    group by 1
)

select
    {{ date_key('days.full_date') }} as date_key,
    days.full_date,
    dayname(days.full_date)              as day_name,
    month(days.full_date)                as month,
    monthname(days.full_date)            as month_name,
    quarter(days.full_date)              as quarter,
    year(days.full_date)                 as year,
    dayofweek(days.full_date) in (0, 6)  as is_weekend,
    holidays.holiday_date is not null    as is_public_holiday,
    holidays.holiday_name
from days
left join holidays on holidays.holiday_date = days.full_date