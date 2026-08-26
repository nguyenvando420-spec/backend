import http from 'k6/http';
import { check } from 'k6';

// Cấu hình kiểm thử tải GET với PostgreSQL (100.000 records)
export const options = {
  scenarios: {
    // 1. Test tải 1200 RPS đọc danh sách có phân trang
    list_items_1200rps: {
      executor: 'constant-arrival-rate',
      rate: 1200,
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      exec: 'testListItems',
    },
    // 2. Test tải 2000 RPS đọc chi tiết theo Primary Key ID
    detail_items_2000rps: {
      executor: 'constant-arrival-rate',
      rate: 2000,
      timeUnit: '1s',
      duration: '10s',
      startTime: '11s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      exec: 'testDetailItem',
    },
    // 3. Test tải 1000 RPS phân trang sâu giữa 100.000 dòng (Deep Pagination: skip 50.000)
    deep_pagination_1000rps: {
      executor: 'constant-arrival-rate',
      rate: 1000,
      timeUnit: '1s',
      duration: '10s',
      startTime: '22s',
      preAllocatedVUs: 50,
      maxVUs: 300,
      exec: 'testDeepPagination',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<100'],
  },
};

const BASE_URL = 'http://127.0.0.1:8000';
const KNOWN_ID = '3e2f6654-004d-47dc-86b1-fa6b4415bd6d';

export function testListItems() {
  const res = http.get(`${BASE_URL}/api/v1/items?limit=20`);
  check(res, {
    'list status 200': (r) => r.status === 200,
    'list has 20 items': (r) => {
      try {
        return JSON.parse(r.body).length === 20;
      } catch (e) {
        return false;
      }
    },
  });
}

export function testDetailItem() {
  const res = http.get(`${BASE_URL}/api/v1/items/${KNOWN_ID}`);
  check(res, {
    'detail status 200': (r) => r.status === 200,
  });
}

export function testDeepPagination() {
  const res = http.get(`${BASE_URL}/api/v1/items?skip=50000&limit=20`);
  check(res, {
    'deep page status 200': (r) => r.status === 200,
  });
}
