import { HttpClient } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";

@Injectable({
  providedIn: "root",
})
export class HttpClientService {
    private httpClient = inject(HttpClient); 

    getThumbnailAndDurationUrl(videoId: string, thumbnailId?: string) {
        return this.httpClient.get(environment.backend_api + environment.videopage_thumbnail_api, {
            responseType: 'blob',
            observe: 'response',
            params: {
                video_id: videoId,
                thumbnail_id: thumbnailId ?? '',
            },
            withCredentials: false
        });
    }
}