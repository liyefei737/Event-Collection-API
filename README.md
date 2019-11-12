# Event-Collection-API
A serverless backend  to collect events using AWS lambda

API Usage:
1. query events by city and/or country

	e.g by city https://url/?city=Chicago

	e.g by country https://url/?country=Canada

	e.g by city and country https://url/?city=Toronto&country=United%20States

2. query by time range
	e.g. https://url/?startDateTime=2019-11-11T02:44:44&endDateTime=2019-11-13T20:11:52

Tests:
https://documenter.getpostman.com/view/282374/SW7T7rYy?version=latest#6702efc2-82b7-4d06-bca1-c5951488319e

AWS Serverless backend using Lambda, API Gateway and DynamoDB:
![AWS Serverless Backend
](https://drive.google.com/uc?export=view&id=13NkCuWqbmc56vGn5ODr9ptADBY7-ZqoO)

In DynamoDB, each event is stored as an item and it has the following fields:
created_date(Partition Key), created_time(Sort Key), ip, name, city, country, location, additional_info. The API also makes use of 2 GSIs that use city and country attribute as Primary key respectively. Geolocation API docker container is deployed using AWS ECS. 

