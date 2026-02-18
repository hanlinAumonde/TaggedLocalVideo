import { HttpHandler, HttpInterceptor, HttpRequest } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";
import { catchError } from "rxjs";
import { ToastService } from "../../services/toast-service/toast.service";

@Injectable({
  providedIn: "root",
})
export class ImageRequestInterceptor implements HttpInterceptor {
    private toastService = inject(ToastService);

    intercept(req: HttpRequest<any>, next: HttpHandler) {
        return next.handle(req).pipe(
            catchError((error) => {
                if(req.url.includes(environment.videopage_thumbnail_api)) {
                    this.toastService.emitErrorOrWarning(
                        `Failed to load video thumbnail image or video duration - video_id: ${req.params.get('video_id')}`,
                        'error'
                    );
                }else if(req.url.includes(environment.video_stream_api)) {
                    this.toastService.emitErrorOrWarning(
                        `Failed to load video stream - video_id: ${req.params.get('video_id')}`,
                        'error'
                    );
                }
                throw error;
            })
        );
    }
}