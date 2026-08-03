import { pipelineApi, pipelineEndpoints } from './pipelineApi';
import { sessionStorage } from './session';

const TOKEN_KEY = 'pipeline_access_token';
const USER_KEY = 'pipeline_user';

export const authService = {
  register: (payload) => pipelineApi.post(pipelineEndpoints.auth.register, payload),
  login: (payload) => pipelineApi.post(pipelineEndpoints.auth.login, payload),
  me: () => pipelineApi.get(pipelineEndpoints.auth.me),
  logout: () => pipelineApi.post(pipelineEndpoints.auth.logout),
};

