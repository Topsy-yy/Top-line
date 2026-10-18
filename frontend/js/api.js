/**
 * TopLine Frontend API Client
 * Manages authentication tokens, JSON REST queries, multipart file uploads,
 * and unified error responses.
 */
class ApiClient {
  constructor(baseUrl = '/api/v1') {
    this.baseUrl = baseUrl;
  }

  getToken() {
    return localStorage.getItem('topline_token');
  }

  setToken(token) {
    if (token) {
      localStorage.setItem('topline_token', token);
    } else {
      localStorage.removeItem('topline_token');
    }
  }

  getHeaders(isMultipart = false) {
    const headers = {};
    if (!isMultipart) {
      headers['Content-Type'] = 'application/json';
    }
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const isMultipart = options.body instanceof FormData;
    const url = `${this.baseUrl}${endpoint}`;
    const headers = { ...this.getHeaders(isMultipart), ...(options.headers || {}) };

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(url, config);
      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        let errorMsg = 'An error occurred';
        if (data && data.detail) {
          if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(e => e.msg || e.message).join(', ');
          } else {
            errorMsg = data.detail;
          }
        } else if (typeof data === 'string') {
          errorMsg = data;
        }
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
      }

      return data;
    } catch (err) {
      throw err;
    }
  }

  // Public Jobs
  getJobs(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/jobs${query ? '?' + query : ''}`);
  }

  getJob(jobId) {
    return this.request(`/jobs/${jobId}`);
  }

  getCategories() {
    return this.request('/jobs/categories');
  }

  getCountries() {
    return this.request('/jobs/countries');
  }

  // Registration & Auth
  register(payload) {
    return this.request('/registrations', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  verifyPhone(phone, otpCode) {
    return this.request('/auth/phone/verify', {
      method: 'POST',
      body: JSON.stringify({ phone, otp_code: otpCode })
    });
  }

  login(phone, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ phone, password })
    });
  }

  logout() {
    this.setToken(null);
    return this.request('/auth/logout', { method: 'POST' });
  }

  // Worker Me
  getMyProfile() {
    return this.request('/workers/me');
  }

  getMyAccess() {
    return this.request('/workers/me/access');
  }

  getMyApplications() {
    return this.request('/workers/me/applications');
  }

  // Payments
  initiatePayment(phone) {
    return this.request('/payments', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phone })
    });
  }

  getPaymentStatus(paymentId) {
    return this.request(`/payments/${paymentId}`);
  }

  mockConfirmPayment(paymentId) {
    return this.request('/payments/mock/confirm', {
      method: 'POST',
      body: JSON.stringify({ payment_id: paymentId })
    });
  }

  // Applications
  submitApplication(jobId, coverLetter) {
    return this.request(`/jobs/${jobId}/applications`, {
      method: 'POST',
      body: JSON.stringify({ cover_letter: coverLetter })
    });
  }

  uploadDocument(applicationId, documentType, file) {
    const formData = new FormData();
    formData.append('document_type', documentType);
    formData.append('file', file);
    return this.request(`/applications/${applicationId}/documents`, {
      method: 'POST',
      body: formData
    });
  }
}

window.apiClient = new ApiClient();

