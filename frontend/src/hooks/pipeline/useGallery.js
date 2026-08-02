import { useQuery } from '@tanstack/react-query';
import { galleryService } from '@/services/miscService';

export function useGallery() {
  return useQuery({
    queryKey: ['gallery'],
    queryFn: galleryService.list,
  });
}

export function usePublicGallery() {
  return useQuery({
    queryKey: ['gallery', 'public'],
    queryFn: galleryService.public,
  });
}
