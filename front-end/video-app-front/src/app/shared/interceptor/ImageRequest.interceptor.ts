import { HttpHandler, HttpInterceptor, HttpRequest } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";
import { catchError } from "rxjs";
import { ErrorHandlerService } from "../../services/errorHandler-service/error-handler-service";

@Injectable({
  providedIn: "root",
})
export class ImageRequestInterceptor implements HttpInterceptor {
    private errorHandler = inject(ErrorHandlerService);

    intercept(req: HttpRequest<any>, next: HttpHandler) {
        return next.handle(req).pipe(
            catchError((error) => {
                if(req.url.includes(environment.videopage_thumbnail_api)) {
                    this.errorHandler.emitError(
                        `Failed to load video thumbnail image or video duration - video_id: ${req.params.get('video_id')}`
                    );
                }else if(req.url.includes(environment.video_stream_api)) {
                    this.errorHandler.emitError(
                        `Failed to load video stream - video_id: ${req.params.get('video_id')}`
                    );
                }
                throw error;
            })
        );
    }
}