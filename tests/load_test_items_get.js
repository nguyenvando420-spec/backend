import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 1200,
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'], // http errors should be less than 5%
    http_req_duration: ['p(95)<1000'], // 95% of requests should be below 1s
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/v1/items');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
