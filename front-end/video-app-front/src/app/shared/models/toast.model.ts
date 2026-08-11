export enum ToastType {
  Error = 'error',
  Warning = 'warning',
  Success = 'success',
}

export interface Toast {
  id: number;
  message: string;
  removing?: boolean;
  type: ToastType;
}