# Public API Guide

## Authentication
All requests use a bearer token in the Authorization header.
Create API tokens in the developer dashboard; tokens expire after 90 days.

## Rate limits
The default rate limit is 100 requests per minute per token.
Exceeding the limit returns HTTP 429 with a Retry-After header.

## Pagination
List endpoints return 50 items per page. Use the `cursor` parameter from the previous
response to fetch the next page.
