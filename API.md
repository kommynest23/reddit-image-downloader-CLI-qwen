# VK API Integration Guide

This document details how the VK Media Downloader CLI integrates with the VK API.

## API Endpoint

All requests are made to: `https://api.vk.com/method/`

## Authentication

Authentication is done using a service token passed as a query parameter:
- Parameter: `access_token`
- Value: Your VK service token
- Required for all API calls

API version is specified as:
- Parameter: `v`
- Default value: `5.199`

## Rate Limiting

VK API has strict rate limits:
- Maximum 3 requests per second per method
- Exceeding this limit results in error code 6 or 9
- Our implementation enforces a maximum of 3 requests per second

## Supported Methods

### Photos
- `photos.get` - Get photos from user albums
- `photos.search` - Search public photos

Parameters for `photos.get`:
- `owner_id` - User or group ID whose photos to retrieve
- `album_id` - Album ID (use "wall" for wall photos)
- `extended` - 1 to return extended info, 0 otherwise
- `count` - Number of photos to return (max 200)
- `offset` - Offset for pagination
- `photo_sizes` - 1 to return all available sizes

### Wall Posts
- `wall.get` - Get wall posts from user or group

Parameters for `wall.get`:
- `owner_id` - User or group ID whose wall to retrieve
- `count` - Number of posts to return (max 100)
- `offset` - Offset for pagination

### Users
- `users.get` - Get user information

Parameters for `users.get`:
- `user_ids` - Comma-separated list of user IDs or screen names
- `fields` - Comma-separated list of additional fields to return

## Error Handling

VK API returns errors in the following format:
```json
{
  "error": {
    "error_code": 123,
    "error_msg": "Error message",
    "request_params": [...]
  }
}
```

Common error codes:
- `6` - Too many requests per second
- `9` - Flood control
- `14` - Captcha needed
- `15` - Access denied

Our client handles these errors appropriately:
- Error 6: Waits 1 second and retries once
- Error 9: Waits 5 seconds and raises an exception
- Error 14: Raises an exception requiring manual CAPTCHA resolution
- Error 15: Raises an access denied exception

## Response Format

Successful responses follow this format:
```json
{
  "response": {
    // Response data
  }
}
```

For example, `photos.get` returns:
```json
{
  "response": {
    "count": 100,
    "items": [
      {
        "id": 123456,
        "owner_id": 789012,
        // ... photo properties
      }
    ]
  }
}
```

## Photo Sizes

VK provides multiple sizes for each photo with different dimensions and quality:
- `s` - Small (up to 75px)
- `m` - Medium (up to 130px)
- `x` - Large X (up to 604px)
- `o` - Original O (up to 130px, cropped)
- `p` - Original P (up to 200px, cropped)
- `q` - Original Q (up to 320px, cropped)
- `r` - Original R (up to 510px, cropped)
- `y` - Extra large Y (up to 807px)
- `z` - Extra large Z (up to 1280px)
- `w` - Maximum W (up to 2560px)

The client automatically selects the largest available size based on pixel dimensions.