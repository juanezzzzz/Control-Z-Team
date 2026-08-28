import { Component, HostListener, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  menuAbierto = signal(false);
  desplazado = signal(false);
  anio = new Date().getFullYear();

  @HostListener('window:scroll')
  alDesplazar() {
    this.desplazado.set(window.scrollY > 8);
  }

  alternarMenu() {
    this.menuAbierto.update(v => !v);
  }

  cerrarMenu() {
    this.menuAbierto.set(false);
  }

  @HostListener('document:keydown.escape')
  alEscape() {
    this.cerrarMenu();
  }
}
