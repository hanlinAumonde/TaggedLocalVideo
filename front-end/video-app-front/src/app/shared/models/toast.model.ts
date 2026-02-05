export interface Toast {
  id: number;
  message: string;
  removing?: boolean;
  type: 'error' | 'warning';
}