# Beem Africa SMS Provider Integration Guide

API documentation for **Beem Africa SMS Gateway** integration.

## 1. Specifications

- **API Version:** v1
- **Base Endpoint:** `https://api.beem.africa/v1/send-sms`
- **Authentication:** Basic Auth (`base64(api_key:secret_key)`)

## 2. Request Structure

```json
{
  "source_addr": "Usimamizi",
  "encoding": 0,
  "schedule_time": "",
  "message": "Your Wi-Fi voucher: K7PM-4XQ9",
  "recipients": [
    {
      "recipient_id": 1,
      "dest_addr": "255712345678"
    }
  ]
}
```

## 3. Response Mapping

- Success Code: `100` (`Message Submitted Successfully`)
- Request Reference: `request_id` mapped to `provider_reference`
