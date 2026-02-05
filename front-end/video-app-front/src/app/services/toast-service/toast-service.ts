import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Toast } from '../../shared/models/toast.model';

@Injectable({
  providedIn: 'root',
})
export class ToastService {
  private counter = 0;

  private _toasts = signal<Toast[]>([]);
  toasts = this._toasts.asReadonly();

  private _toastBeyondDialog = signal<Toast[]>([]);
  toastBeyondDialog = this._toastBeyondDialog.asReadonly();

  emitErrorOrWarning(message: string, type: 'error' | 'warning' = 'error', beyondDialog: boolean = false) {
    const id = ++this.counter;

    const updateFn = beyondDialog ? this._toastBeyondDialog.update : this._toasts.update;

    updateFn(list => {
      const newList = [...list, { id, message, type }];
      // when exceeding max toasts, remove the oldest one
      if (newList.length > environment.ERROR_TOAST_SETTINGS.MAX_TOASTS) {
        const oldest = newList.find(t => !t.removing);
        if (oldest) {
          oldest.removing = true;
          setTimeout(() => this.removeToast(oldest.id, beyondDialog), environment.ERROR_TOAST_SETTINGS.EXIT_ANIMATION_MS);
        }
      }
      return newList;
    });

    // close automatically after a delay
    setTimeout(() => this.dismiss(id, beyondDialog), environment.ERROR_TOAST_SETTINGS.AUTO_DISMISS_MS);
  }

  dismiss(id: number, beyondDialog: boolean = false) {
    const updateFn = beyondDialog ? this._toastBeyondDialog.update : this._toasts.update;
    // marked as removing to trigger exit animation
    updateFn(list =>
      list.map(t => (t.id === id ? { ...t, removing: true } : t))
    );
    // remove after animation ends
    setTimeout(() => this.removeToast(id), environment.ERROR_TOAST_SETTINGS.EXIT_ANIMATION_MS);
  }

  private removeToast(id: number, beyondDialog: boolean = false) {
    const updateFn = beyondDialog ? this._toastBeyondDialog.update : this._toasts.update;
    updateFn(list => list.filter(t => t.id !== id));
  }

  public clearAllToastsBeyondDialog() {
    this._toastBeyondDialog().forEach(t => {
      this.removeToast(t.id, true);
    });
  }

  public clearAllToasts() {
    this._toasts().forEach(t => {
      this.removeToast(t.id);
    });
  }
}
