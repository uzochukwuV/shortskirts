import { useEffect, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authService, authStorage } from '@/services/authService';

const authKeys = {
  me: ['auth', 'me'],
};

export function useAuthSession() {
  const queryClient = useQueryClient();
  const token = authStorage.getToken();
  const storedUser = authStorage.getUser();

  const meQuery = useQuery({
    queryKey: authKeys.me,
    queryFn: authService.me,
    enabled: Boolean(token),
    initialData: token && storedUser ? storedUser : undefined,
  });

  useEffect(() => {
    if (!token) {
      queryClient.removeQueries({ queryKey: authKeys.me });
    }
  }, [queryClient, token]);

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: (data) => {
      authStorage.setSession(data.token, data.user);
      queryClient.setQueryData(authKeys.me, data.user);
    },
  });

  const registerMutation = useMutation({
    mutationFn: authService.register,
    onSuccess: (data) => {
      authStorage.setSession(data.token, data.user);
      queryClient.setQueryData(authKeys.me, data.user);
    },
  });

  const logoutMutation = useMutation({
    mutationFn: authService.logout,
    onSettled: () => {
      authStorage.clear();
      queryClient.removeQueries({ queryKey: authKeys.me });
    },
  });

  const user = meQuery.data ?? storedUser ?? null;
  const isAuthenticated = Boolean(token && user);
  const isLoading = meQuery.isLoading || loginMutation.isPending || registerMutation.isPending || logoutMutation.isPending;

  return {
    token,
    user,
    isAuthenticated,
    isLoading,
    isMeLoading: meQuery.isLoading,
    error: meQuery.error || loginMutation.error || registerMutation.error || logoutMutation.error,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout: async () => {
      await logoutMutation.mutateAsync();
    },
    refreshUser: () => meQuery.refetch(),
    clearSession: () => {
      authStorage.clear();
      queryClient.removeQueries({ queryKey: authKeys.me });
    },
  };
}

export const authKeys = authKeys;
