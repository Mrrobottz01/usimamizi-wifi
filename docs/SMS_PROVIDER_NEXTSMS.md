# NextSMS (Provider A) Tanzania Integration Guide

API documentation for **NextSMS Tanzania API V2** integration.

## 1. Specifications

- **API Version:** V2
- **Base Endpoint:** `https://messaging-service.co.tz/api/sms/v2/text/single`
- **Authentication:** Bearer Token (`Authorization: Bearer <API_TOKEN>`)

## 2. Request Structure

```json
{
  "from": "Usimamizi",
  "to": "255712345678",
  "text": "Your Wi-Fi voucher: K7PM-4XQ9"
}
```

## 3. Response Mapping

- Message Status Group: `PENDING`, `DELIVERY`, `SENT`
- Message Reference: `messages[0].messageId`
