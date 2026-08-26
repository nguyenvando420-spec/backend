import http from 'k6/http';
import { check } from 'k6';

// Test tải ổn định 3000 RPS vào DB
export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 3000,
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 100,
      maxVUs: 400,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<100'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/v1/items?limit=5');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
