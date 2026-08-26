import http from 'k6/http';
import { check } from 'k6';

// Kịch bản Stress Test tìm tải tối đa của Endpoint GET /
export const options = {
  scenarios: {
    stress_ramp_up: {
      executor: 'ramping-arrival-rate',
      startRate: 2000,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 800,
      stages: [
        { target: 3000, duration: '5s' },
        { target: 5000, duration: '5s' },
        { target: 8000, duration: '5s' },
        { target: 10000, duration: '5s' },
        { target: 12000, duration: '5s' },
      ],
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
