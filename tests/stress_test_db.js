import http from 'k6/http';
import { check } from 'k6';

// Stress test endpoint truy vấn DB để tìm giới hạn tối đa không lỗi
export const options = {
  scenarios: {
    stress_db_ramp_up: {
      executor: 'ramping-arrival-rate',
      startRate: 2000,
      timeUnit: '1s',
      preAllocatedVUs: 100,
      maxVUs: 800,
      stages: [
        { target: 3000, duration: '5s' },
        { target: 4000, duration: '5s' },
        { target: 5000, duration: '5s' },
        { target: 6000, duration: '5s' },
        { target: 7000, duration: '5s' },
        { target: 8000, duration: '5s' },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://127.0.0.1:8000/api/v1/items?limit=5');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
