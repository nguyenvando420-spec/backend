import http from 'k6/http';
import { check } from 'k6';

// Test tải cực đại 15.000 RPS vào root endpoint
export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 15000,
      timeUnit: '1s',
      duration: '5s',
      preAllocatedVUs: 200,
      maxVUs: 1000,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
