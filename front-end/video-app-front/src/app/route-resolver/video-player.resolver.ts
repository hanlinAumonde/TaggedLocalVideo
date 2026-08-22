import { 
    ActivatedRouteSnapshot, 
    RedirectCommand, 
    ResolveFn, 
    Router, 
    RouterStateSnapshot 
} from "@angular/router";
import { ResultState, VideoDetail } from "../shared/models/GQL-result.model";
import { inject } from "@angular/core";
import { GqlService } from "../services/GQL-service/GQL.service";
import { of, switchMap, filter } from "rxjs";
import { environment } from "../../environments/environment";
import { ToastService } from "../services/toast-service/toast.service";
import { ToastType } from "../shared/models/toast.model";

export const VideoMetaDataResolver: ResolveFn<ResultState<VideoDetail | null> | RedirectCommand> = (
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
) => {
    const gqlService = inject(GqlService);
    const router = inject(Router);
    const toastService = inject(ToastService);

    const videoId = route.paramMap.get('id') ?? '';
    if(!videoId){
        toastService.emitNewToast('Null video ID', ToastType.Error);
        return new RedirectCommand(router.parseUrl(environment.homepage_api));
    }
    return gqlService.getVideoByIdQuery(videoId).pipe(
        filter(result => !result.loading),
        switchMap(result => {
            if (result.error) {
                toastService.emitNewToast(
                    `Failed to resolve video metadata: ${result.error}`,
                    ToastType.Error
                );
                return of(new RedirectCommand(router.parseUrl(environment.homepage_api)));
            }
            // Playback is blocked for the whole migration, not just the delete step: the
            // source file disappears partway through and the player would break mid-stream.
            if (result.data?.isLocked) {
                toastService.emitNewToast(
                    'This video is being migrated and cannot be played right now.',
                    ToastType.Warning
                );
                return of(new RedirectCommand(router.parseUrl(environment.homepage_api)));
            }
            return of(result);
        })
    )
}