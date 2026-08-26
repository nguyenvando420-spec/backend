import http from 'k6/http';
import { check } from 'k6';

// Cấu hình k6: Test tải 1200 req/s trực tiếp vào endpoint GET /api/v1/items/{item_id}
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
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<100'],
  },
};

// Lấy ID thật từ hệ thống
const ITEM_ID = 'be94782e-87d3-458f-9dd6-72d02e79c783';

export default function () {
  const res = http.get(`http://127.0.0.1:8000/api/v1/items/${ITEM_ID}`);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
