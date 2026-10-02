-- CAMEROON SMARTTRIP — MVP DOUALA -> KRIBI

SELECT name, price_from, price_currency, beach_access, pool, wifi
FROM hotels
WHERE price_from IS NOT NULL AND price_currency='XAF'
ORDER BY price_from;

SELECT name, price_from, price_currency, key_features
FROM hotels
WHERE lower(beach_access) LIKE '%oui%' AND lower(pool) LIKE '%oui%';

SELECT provider, name, duration_text, price_from, price_currency
FROM activities
WHERE price_from IS NOT NULL
ORDER BY price_currency, price_from;

SELECT operator, service_class, one_way_price, round_trip_price, currency, departures
FROM transport
WHERE origin='Douala' AND destination='Kribi'
ORDER BY one_way_price;

SELECT dataset, source_type, verified_on, source_url
FROM data_sources
ORDER BY dataset, source_id;
