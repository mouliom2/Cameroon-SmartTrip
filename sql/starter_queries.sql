
-- Hôtels réellement tarifés et utilisables par le moteur
SELECT name, price_from_xaf, price_confidence, beach_access, pool, wifi
FROM vw_budget_hotels
ORDER BY CAST(price_from_xaf AS REAL);

-- Transport Douala -> Kribi
SELECT operator, service_class, one_way_price, round_trip_price, departures
FROM transport
ORDER BY CAST(round_trip_price AS REAL);

-- Restaurants avec prix XAF publié
SELECT name, price_from_xaf, sample_prices, source_url
FROM restaurants
WHERE price_from_xaf IS NOT NULL
ORDER BY CAST(price_from_xaf AS REAL);

-- Traçabilité des sources
SELECT dataset, source_type, verified_on, source_url
FROM data_sources
ORDER BY dataset, source_id;
