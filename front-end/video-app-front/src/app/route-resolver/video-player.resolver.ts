import { ActivatedRouteSnapshot, 
         RedirectCommand, 
         ResolveFn, 
         Router, 
         RouterStateSnapshot } from "@angular/router";
import { ResultState, VideoDetail } from "../shared/models/GQL-result.model";
import { inject } from "@angular/core";
import { GqlService } from "../services/GQL-service/GQL-service";
import { of, switchMap, filter } from "rxjs";
import { environment } from "../../environments/environment";

export const VideoMetaDataResolver: ResolveFn<ResultState<VideoDetail | null> | RedirectCommand> = (
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
) => {
    const gqlService = inject(GqlService);
    const router = inject(Router);

    const videoId = route.paramMap.get('id') ?? '';
    console.log('Resolving video metadata for video ID:', videoId);
    if(!videoId){
        window.alert('Null video ID');
        return new RedirectCommand(router.parseUrl(environment.homepage_api));
    }
    return gqlService.getVideoByIdQuery(videoId).pipe(
        filter(result => !result.loading),
        //first(),
        switchMap(result => {
            if (result.error) {
                return of(new RedirectCommand(router.parseUrl(environment.homepage_api)))
            }
            console.log('Resolved video metadata:', result);
            return of(result);
        })
    )
}