"""Dialog windows for overlay settings, about, and image generation."""

import base64
import re
import tempfile
import threading
from datetime import datetime
from typing import Callable, Optional

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
import structlog

logger = structlog.get_logger(__name__)


class AboutDialog:
    """About dialog for the overlay."""

    @staticmethod
    def show(parent_window, config):
        """Show the about dialog.

        Args:
            parent_window: Parent window for modal dialog
            config: Overlay configuration
        """
        try:
            # Try Gtk.AboutDialog (GTK4)
            if hasattr(Gtk, "AboutDialog"):
                d = Gtk.AboutDialog()
                d.set_program_name("Neuralux")
                try:
                    import importlib

                    ver = importlib.import_module("overlay").__version__
                except Exception:
                    ver = "0.1.0"
                d.set_version(ver)

                # Logo
                try:
                    import os as _os

                    logo_path = str(
                        __import__("pathlib").Path(__file__).parent
                        / "assets"
                        / "neuralux-tray.svg"
                    )
                    if _os.path.exists(logo_path):
                        try:
                            # Prefer native GTK4 paintable via Gdk.Texture
                            tex = Gdk.Texture.new_from_file(
                                Gio.File.new_for_path(logo_path)
                            )
                            d.set_logo(tex)
                        except Exception:
                            # Fallback to pixbuf → texture
                            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(
                                logo_path, 196, 196
                            )
                            try:
                                tex2 = Gdk.Texture.new_for_pixbuf(pb)
                                d.set_logo(tex2)
                            except Exception:
                                pass
                except Exception:
                    pass

                d.set_comments("Neuralux AI Layer – Desktop assistant overlay")
                d.set_modal(True)
                d.set_transient_for(parent_window)
                d.show()
                return
        except Exception:
            pass

        # Fallback simple window
        try:
            w = Gtk.Window(title=f"About {config.app_name}")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_margin_top(16)
            box.set_margin_bottom(16)
            box.set_margin_start(16)
            box.set_margin_end(16)
            lab = Gtk.Label(label=f"{config.app_name}\nVersion 0.1.0")
            lab.set_halign(Gtk.Align.CENTER)
            box.append(lab)
            w.set_child(box)
            w.set_transient_for(parent_window)
            w.present()
        except Exception:
            pass


class SettingsDialog:
    """Settings dialog for overlay configuration."""

    @staticmethod
    def show(
        parent_window,
        config,
        on_command: Callable[[str], None],
        begin_busy: Callable[[str], None],
        end_busy: Callable[[str], None],
        show_toast: Callable[[str], None],
        set_status: Callable[[str], None],
    ):
        """Show the settings dialog.

        Args:
            parent_window: Parent window for modal dialog
            config: Overlay configuration
            on_command: Callback to execute commands
            begin_busy: Callback to show busy state
            end_busy: Callback to hide busy state
            show_toast: Callback to show toast notification
            set_status: Callback to set status message
        """
        try:
            from neuralux.memory import SessionStore
            from neuralux.config import NeuraluxConfig

            cfg = NeuraluxConfig()
            store = SessionStore(cfg)
            current = store.load_settings(cfg.settings_path())
        except Exception:
            current = {}

        llm_default = current.get("llm_model", "llama-3.2-3b-instruct-q4_k_m.gguf")
        stt_default = current.get("stt_model", "medium")

        w = Gtk.Window(title="Settings")
        w.set_transient_for(parent_window)
        w.set_default_size(500, 450)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vb.set_margin_top(12)
        vb.set_margin_bottom(12)
        vb.set_margin_start(12)
        vb.set_margin_end(12)

        # LLM model
        llm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        llm_row.append(Gtk.Label(label="LLM model file:"))
        llm_entry = Gtk.Entry()
        llm_entry.set_text(llm_default)
        llm_row.append(llm_entry)
        vb.append(llm_row)

        # Quick model family selection
        fam_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fam_row.append(Gtk.Label(label="Quick select:"))
        btn_llama = Gtk.Button(label="Llama 3B")
        btn_mistral = Gtk.Button(label="Mistral 7B")
        try:
            btn_llama.connect(
                "clicked",
                lambda _b: llm_entry.set_text("llama-3.2-3b-instruct-q4_k_m.gguf"),
            )
            btn_mistral.connect(
                "clicked",
                lambda _b: llm_entry.set_text("mistral-7b-instruct-q4_k_m.gguf"),
            )
        except Exception:
            pass
        fam_row.append(btn_llama)
        fam_row.append(btn_mistral)
        vb.append(fam_row)

        # Download Mistral helper
        dl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dl_btn = Gtk.Button(label="Download Mistral 7B Q4_K_M")
        dl_note = Gtk.Label(label="(downloads to models/; size ~4GB)")
        dl_row.append(dl_btn)
        dl_row.append(dl_note)
        vb.append(dl_row)

        # STT model
        stt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stt_row.append(Gtk.Label(label="STT model:"))
        stt_combo = Gtk.ComboBoxText()
        for name in ["tiny", "base", "small", "medium", "large"]:
            stt_combo.append_text(name)
        try:
            stt_combo.set_active(
                ["tiny", "base", "small", "medium", "large"].index(stt_default)
                if stt_default in ["tiny", "base", "small", "medium", "large"]
                else 3
            )
        except Exception:
            pass
        stt_row.append(stt_combo)
        vb.append(stt_row)

        # Separator
        sep = Gtk.Separator()
        vb.append(sep)

        # Image Generation Settings
        img_gen_label = Gtk.Label()
        img_gen_label.set_markup("<b>Image Generation</b>")
        img_gen_label.set_halign(Gtk.Align.START)
        vb.append(img_gen_label)

        # Image gen model
        img_model_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_model_row.append(Gtk.Label(label="Model:"))
        img_model_combo = Gtk.ComboBoxText()
        for name in ["flux-schnell (fast)", "flux-dev (quality)", "sdxl-lightning"]:
            img_model_combo.append_text(name)
        img_model_default = current.get("image_gen_model", "flux-schnell")
        try:
            idx = ["flux-schnell", "flux-dev", "sdxl-lightning"].index(
                img_model_default
            )
            img_model_combo.set_active(idx)
        except Exception:
            img_model_combo.set_active(0)
        img_model_row.append(img_model_combo)
        vb.append(img_model_row)

        # Image size
        img_size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_size_row.append(Gtk.Label(label="Size:"))
        img_size_combo = Gtk.ComboBoxText()
        for size in ["512x512", "768x768", "1024x768", "768x1024", "1024x1024"]:
            img_size_combo.append_text(size)
        size_default = f"{current.get('image_gen_width', 1024)}x{current.get('image_gen_height', 1024)}"
        try:
            img_size_combo.set_active(
                ["512x512", "768x768", "1024x768", "768x1024", "1024x1024"].index(
                    size_default
                )
            )
        except Exception:
            img_size_combo.set_active(4)  # 1024x1024
        img_size_row.append(img_size_combo)
        vb.append(img_size_row)

        # Steps
        img_steps_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_steps_row.append(Gtk.Label(label="Steps:"))
        img_steps_spin = Gtk.SpinButton()
        img_steps_spin.set_range(1, 50)
        img_steps_spin.set_increments(1, 5)
        img_steps_spin.set_value(current.get("image_gen_steps", 4))
        img_steps_row.append(img_steps_spin)
        vb.append(img_steps_row)

        # Status label
        info = Gtk.Label(label="")
        vb.append(info)

        # Buttons
        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_btn = Gtk.Button(label="Apply")
        save_btn = Gtk.Button(label="Save Defaults")
        close_btn = Gtk.Button(label="Close")
        btns.append(apply_btn)
        btns.append(save_btn)
        btns.append(close_btn)
        vb.append(btns)

        def _apply(_b):
            try:
                begin_busy("Applying settings…")
            except Exception:
                pass

            try:
                on_command(f"/set llm.model {llm_entry.get_text().strip()}")
                sel = stt_combo.get_active_text()
                if sel:
                    on_command(f"/set stt.model {sel}")

                # Image generation settings
                img_model_text = (
                    img_model_combo.get_active_text() or "flux-schnell (fast)"
                )
                img_model = img_model_text.split(" ")[0]
                on_command(f"/set image_gen.model {img_model}")

                img_size_text = img_size_combo.get_active_text() or "1024x1024"
                width, height = map(int, img_size_text.split("x"))
                on_command(f"/set image_gen.width {width}")
                on_command(f"/set image_gen.height {height}")

                steps = int(img_steps_spin.get_value())
                on_command(f"/set image_gen.steps {steps}")

                info.set_text("Applied. Models will reload if required.")
            except Exception as e:
                info.set_text(f"Failed to apply: {e}")
            finally:
                try:
                    end_busy("Ready")
                except Exception:
                    pass

        def _save(_b):
            try:
                begin_busy("Saving settings…")
            except Exception:
                pass

            try:
                # First apply, then save
                _apply(None)
                on_command("/settings.save")
                info.set_text("Saved defaults.")
                show_toast("Settings saved")
            except Exception as e:
                info.set_text(f"Failed to save: {e}")
            finally:
                try:
                    end_busy("Ready")
                except Exception:
                    pass

        def _close(_b):
            try:
                w.close()
            except Exception:
                pass

        try:
            apply_btn.connect("clicked", _apply)
            save_btn.connect("clicked", _save)
            close_btn.connect("clicked", _close)
        except Exception:
            pass

        # Download Mistral logic
        def _download_mistral(_b):
            try:
                begin_busy("Downloading Mistral 7B…")
            except Exception:
                pass

            def _worker():
                url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

                try:
                    from pathlib import Path as _P

                    base = (_P(__file__).parent.parent.parent / "models").resolve()
                except Exception:
                    from pathlib import Path as _P

                    base = _P.home() / "models"

                base.mkdir(parents=True, exist_ok=True)
                target = base / "mistral-7b-instruct-q4_k_m.gguf"

                try:
                    import httpx

                    with httpx.stream(
                        "GET", url, follow_redirects=True, timeout=None
                    ) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", "0")) or None
                        downloaded = 0
                        with open(target, "wb") as f:
                            for chunk in r.iter_bytes(chunk_size=1_048_576):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if total:
                                        pct = int(downloaded * 100 / total)
                                        GLib.idle_add(
                                            lambda p=pct: set_status(
                                                f"Downloading Mistral… {p}%"
                                            )
                                        )

                    GLib.idle_add(
                        lambda: (
                            llm_entry.set_text(target.name),
                            show_toast("Mistral downloaded"),
                            end_busy("Ready"),
                        )
                    )
                except Exception as e:
                    GLib.idle_add(
                        lambda: (end_busy("Ready"), show_toast(f"Download failed: {e}"))
                    )

            threading.Thread(target=_worker, daemon=True).start()

        try:
            dl_btn.connect("clicked", _download_mistral)
        except Exception:
            pass

        w.set_child(vb)
        try:
            w.present()
        except Exception:
            pass


class ImageGenerationManager:
    """Manages inline image generation in the overlay."""

    @staticmethod
    def generate_and_display(
        prompt: str,
        parent_window,
        clear_results: Callable,
        add_result: Callable,
        begin_busy: Callable,
        end_busy: Callable,
        show_toast: Callable,
        results_list,
    ):
        """Generate image and display inline in results.

        Args:
            prompt: Image generation prompt
            parent_window: Parent window for dialogs
            clear_results: Callback to clear results list
            add_result: Callback to add result row
            begin_busy: Callback to show busy state
            end_busy: Callback to hide busy state
            show_toast: Callback to show toast
            results_list: GTK ListBox for results
        """
        try:
            clear_results()
            begin_busy("Generating image...")

            # Get settings
            try:
                from neuralux.memory import SessionStore
                from neuralux.config import NeuraluxConfig

                cfg = NeuraluxConfig()
                store = SessionStore(cfg)
                settings = store.load_settings(cfg.settings_path())

                width = settings.get("image_gen_width", 1024)
                height = settings.get("image_gen_height", 1024)
                steps = settings.get("image_gen_steps", 4)
                model = settings.get("image_gen_model", "flux-schnell")
            except Exception:
                width, height, steps, model = 1024, 1024, 4, "flux-schnell"

            # Show generation info
            add_result(
                "Generating Image",
                f"Prompt: {prompt}\nSize: {width}x{height}\nSteps: {steps}\nModel: {model}",
            )

            # Generate in background
            def _gen_worker():
                try:
                    import httpx

                    response = httpx.post(
                        "http://localhost:8005/v1/generate-image",
                        json={
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "num_inference_steps": steps,
                            "model": model,
                        },
                        timeout=600.0,
                    )
                    response.raise_for_status()
                    result = response.json()

                    image_b64 = result.get("image_bytes_b64")
                    if image_b64:
                        # Decode image
                        image_bytes = base64.b64decode(image_b64)

                        # Save to temp file for display
                        with tempfile.NamedTemporaryFile(
                            suffix=".png", delete=False
                        ) as f:
                            f.write(image_bytes)
                            temp_path = f.name

                        def _show_result():
                            try:
                                clear_results()

                                # Create outer box for image row
                                img_box = Gtk.Box(
                                    orientation=Gtk.Orientation.VERTICAL, spacing=8
                                )
                                img_box.set_margin_top(8)
                                img_box.set_margin_bottom(8)

                                # Show prompt above image
                                prompt_label = Gtk.Label()
                                prompt_label.set_markup(f'<b>"{prompt}"</b>')
                                prompt_label.set_wrap(True)
                                prompt_label.set_xalign(0.5)
                                prompt_label.set_margin_bottom(8)
                                img_box.append(prompt_label)

                                # Load and display image
                                try:
                                    # Load pixbuf
                                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(temp_path)

                                    # Scale to fit in overlay (max 400px height, maintain aspect ratio)
                                    orig_width = pixbuf.get_width()
                                    orig_height = pixbuf.get_height()

                                    max_height = 400
                                    if orig_height > max_height:
                                        scale = max_height / orig_height
                                        new_width = int(orig_width * scale)
                                        new_height = max_height
                                        pixbuf = pixbuf.scale_simple(
                                            new_width,
                                            new_height,
                                            GdkPixbuf.InterpType.BILINEAR,
                                        )

                                    # Convert to texture
                                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)

                                    # Create picture widget
                                    picture = Gtk.Picture()
                                    picture.set_paintable(texture)
                                    picture.set_size_request(
                                        pixbuf.get_width(), pixbuf.get_height()
                                    )
                                    picture.set_halign(Gtk.Align.CENTER)
                                    picture.set_valign(Gtk.Align.CENTER)
                                    picture.set_can_shrink(False)
                                    img_box.append(picture)

                                    logger.info(
                                        f"Image loaded: {pixbuf.get_width()}x{pixbuf.get_height()}"
                                    )
                                except Exception as img_err:
                                    logger.error(f"Image display error: {img_err}")
                                    err_label = Gtk.Label(
                                        label=f"Image loaded but display failed: {img_err}\nTemp file: {temp_path}"
                                    )
                                    err_label.set_wrap(True)
                                    img_box.append(err_label)

                                # Store texture for clipboard
                                stored_texture = (
                                    texture if "texture" in locals() else None
                                )

                                # Buttons row
                                btn_box = Gtk.Box(
                                    orientation=Gtk.Orientation.HORIZONTAL, spacing=8
                                )
                                btn_box.set_halign(Gtk.Align.CENTER)
                                btn_box.set_margin_top(8)

                                # Save button
                                save_btn = Gtk.Button(label="💾 Save")

                                def _save(_b):
                                    _save_image(
                                        parent_window, image_bytes, prompt, show_toast
                                    )

                                save_btn.connect("clicked", _save)
                                btn_box.append(save_btn)

                                # Copy to clipboard button
                                copy_btn = Gtk.Button(label="📋 Copy")

                                def _copy(_b):
                                    try:
                                        clipboard = (
                                            Gdk.Display.get_default().get_clipboard()
                                        )
                                        if stored_texture:
                                            clipboard.set_texture(stored_texture)
                                            show_toast("Image copied to clipboard!")
                                        else:
                                            show_toast("No texture available to copy")
                                    except Exception as e:
                                        show_toast(f"Copy failed: {e}")

                                copy_btn.connect("clicked", _copy)
                                btn_box.append(copy_btn)

                                img_box.append(btn_box)

                                # Add to results as a row
                                row = Gtk.ListBoxRow()
                                row.set_child(img_box)
                                row.set_activatable(False)
                                row.set_selectable(False)
                                results_list.append(row)

                                # Make sure the row is visible
                                row.set_visible(True)
                                img_box.set_visible(True)

                                logger.info("Image row added to results list")

                                end_busy("✓ Image generated!")
                                show_toast("Image ready!")
                            except Exception as e:
                                end_busy(f"Display error: {e}")
                            return False

                        GLib.idle_add(_show_result)
                    else:
                        GLib.idle_add(lambda: end_busy("No image returned") or False)

                except Exception as e:
                    GLib.idle_add(
                        lambda err=str(e): end_busy(f"Generation failed: {err}")
                        or False
                    )

            threading.Thread(target=_gen_worker, daemon=True).start()

        except Exception as e:
            end_busy(f"Error: {e}")


def _save_image(parent_window, image_bytes: bytes, prompt: str, show_toast: Callable):
    """Save generated image with file dialog."""
    try:
        dialog = Gtk.FileDialog()
        dialog.set_title("Save Generated Image")

        # Generate filename
        safe_prompt = re.sub(r"[^\w\s-]", "", prompt)[:50]
        safe_prompt = re.sub(r"[-\s]+", "_", safe_prompt)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{safe_prompt}_{timestamp}.png"
        dialog.set_initial_name(default_name)

        def _on_save_finish(dialog, result):
            try:
                file = dialog.save_finish(result)
                if file:
                    path = file.get_path()
                    with open(path, "wb") as f:
                        f.write(image_bytes)
                    show_toast(f"Image saved!")
            except Exception as e:
                if "dismiss" not in str(e).lower():
                    show_toast(f"Save failed: {e}")

        dialog.save(parent_window, None, _on_save_finish)
    except Exception as e:
        show_toast(f"Save error: {e}")
