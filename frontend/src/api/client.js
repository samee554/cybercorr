import axios from 'axios';

const client = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
});

// Response interceptor to unwrap standard data envelope
client.interceptors.response.use(
  (response) => {
    // Check if the response contains success: true and data envelope
    if (response.data && response.data.success) {
      return response.data.data;
    }
    return response.data;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const getAlerts = (page, limit, risk) => {
  const params = {};
  if (page !== undefined) params.page = page;
  if (limit !== undefined) params.limit = limit;
  if (risk) params.risk = risk;
  return client.get('/alerts', { params });
};

export const getAlert = (id) => {
  return client.get(`/alerts/${id}`);
};

export const explainAlert = (id) => {
  return client.post(`/alerts/${id}/explain`);
};

export const updateAlertStatus = (id, status) => {
  return client.post(`/alerts/${id}/status`, { status });
};

export const getGraph = () => {
  return client.get('/graph');
};

export const getQuantumSummary = () => {
  return client.get('/quantum/summary');
};

export const getFraudHeatmap = () => {
  return client.get('/fraud/heatmap');
};

export default client;
