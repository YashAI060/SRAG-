const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const client = {
  token: localStorage.getItem('srag_token'),

  setToken(token) {
    this.token = token;
    localStorage.setItem('srag_token', token);
  },

  logout() {
    this.token = null;
    localStorage.removeItem('srag_token');
  },

  async request(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    // For FormData, let browser set Content-Type with boundary
    if (options.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      if (response.status === 401) {
        this.logout();
        window.location.reload();
      }
      const error = await response.json().catch(() => ({}));
      const detail = typeof error.detail === 'string'
        ? error.detail
        : (error.detail ? JSON.stringify(error.detail) : `HTTP Error ${response.status}`);
      throw new Error(detail);
    }

    return response.json();
  },

  // Auth
  async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });
    
    if (!response.ok) throw new Error('Login failed');
    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  },

  async register(username, email, password) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, role: 'user' })
    });
  },

  // Documents
  async getDocuments() {
    return this.request('/docs/');
  },

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/docs/upload', {
      method: 'POST',
      body: formData
    });
  },

  // Chat
  async ask(query, mode = 'hybrid', decompose = true) {
    return this.request('/chat/ask', {
      method: 'POST',
      body: JSON.stringify({ query: query, retrieval_mode: mode, decompose: decompose })
    });
  }
};
