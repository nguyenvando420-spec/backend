import http from 'k6/http';
import { check } from 'k6';

// Test tải chuyên biệt 1200 RPS đọc phân trang 20 records từ PostgreSQL 100k dòng
export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 1200,
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<100'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/v1/items?limit=20');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has 20 items': (r) => {
      try {
        return JSON.parse(r.body).length === 20;
      } catch (e) {
        return false;
      }
    },
  });
}
