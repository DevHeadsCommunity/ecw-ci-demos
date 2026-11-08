# Frontend-format HIL CSV

The HIL demo branch fixes the sensor to BME280 and loads exactly 50 rows from
`bme280.csv`; its columns match frontend export:
`sample,temperature_c,humidity_pct,pressure_hpa`.

Edit those physical values to change the scenario. The demo requires 50 rows
and verifies all 150 encoded words through the backend, then compares 50
readings over the RA6 SPI bus. No sensor or CSV repository variable is needed.
The other demo branches skip HIL configuration and contain no sample CSV.
