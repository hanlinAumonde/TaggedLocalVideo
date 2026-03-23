export enum ToastType {
  Error = 'error',
  Warning = 'warning',
}

export interface Toast {
  id: number;
  message: string;
  removing?: boolean;
  type: ToastType;
}