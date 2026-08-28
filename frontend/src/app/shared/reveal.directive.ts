import {
  AfterViewInit,
  Directive,
  ElementRef,
  Input,
  OnDestroy,
  Renderer2,
  inject,
} from '@angular/core';

/**
 * `[appReveal]` — el elemento entra con un pequeño desplazamiento hacia arriba
 * y un fundido cuando aparece en el viewport. Una sola vez; después queda fijo.
 *
 * `appReveal` acepta un retardo en ms para escalonar grupos (tarjetas de una
 * grilla, pasos de una lista). Si el usuario pidió menos movimiento, el
 * contenido se muestra de inmediato sin animar.
 */
@Directive({
  selector: '[appReveal]',
  standalone: true,
})
export class RevealDirective implements AfterViewInit, OnDestroy {
  @Input('appReveal') delay: number | string = 0;

  private el = inject(ElementRef<HTMLElement>);
  private renderer = inject(Renderer2);
  private observer?: IntersectionObserver;

  private get reduceMotion(): boolean {
    return (
      typeof matchMedia === 'function' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  ngAfterViewInit(): void {
    const node = this.el.nativeElement;

    if (this.reduceMotion || typeof IntersectionObserver === 'undefined') {
      this.renderer.addClass(node, 'is-visible');
      return;
    }

    this.renderer.addClass(node, 'reveal');
    const ms = Number(this.delay) || 0;
    if (ms) this.renderer.setStyle(node, 'transition-delay', `${ms}ms`);

    this.observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            this.renderer.addClass(node, 'is-visible');
            this.observer?.disconnect();
          }
        }
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    );
    this.observer.observe(node);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}
