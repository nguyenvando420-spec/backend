import http from 'k6/http';
import { check } from 'k6';

// Cấu hình k6: Kiểm thử tải với tốc độ cố định 1200 request/giây
export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 1200,             // 1200 requests
      timeUnit: '1s',          // mỗi giây
      duration: '15s',         // Thời gian chạy test
      preAllocatedVUs: 50,     // Số Virtual Users phân bổ trước
      maxVUs: 300,             // Số Virtual Users tối đa
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],    // Tỉ lệ lỗi phải < 1%
    http_req_duration: ['p(95)<1000'], // 95% request hoàn thành dưới 1000ms
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://127.0.0.1:8000';
const ENDPOINT = __ENV.ENDPOINT || '/api/v1/items?limit=10';

export default function () {
  const url = `${BASE_URL}${ENDPOINT}`;
  const res = http.get(url);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
