import http from 'k6/http';
import { check } from 'k6';

// Cấu hình k6: Kiểm thử tải cao 2400 RPS trên cụm 4 workers
export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 2400,             // 2400 request/s
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 100,
      maxVUs: 400,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<200'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/v1/items?limit=5');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
