import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    constant_request_rate: {
      executor: 'constant-arrival-rate',
      rate: 1200,
      timeUnit: '1s',
      duration: '5s',
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const payload = JSON.stringify({
    title: `Item_${__VU}_${__ITER}`,
    price: 99.9,
    description: 'Load test item',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post('http://127.0.0.1:8000/api/v1/items', payload, params);
  check(res, {
    'status is 201': (r) => r.status === 201,
  });
}
