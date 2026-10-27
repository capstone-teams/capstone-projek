import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InstructorSetupForm from '../src/components/ai/InstructorSetupForm';
import TeachingProfileForm from '../src/components/ai/TeachingProfileForm';
import {
  DEFAULT_ACTIVITY_CONFIGURATION,
  MAX_PROMPT_LENGTH,
} from '../src/components/ai/instructorSetupConstants';
import TeachingPreferencesCard from '../src/components/ai/TeachingPreferencesCard';

const mockInstructorService = vi.hoisted(() => ({
  getInstructorSetup: vi.fn(),
  updateInstructorSetup: vi.fn(),
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock('../src/services/instructorService', () => mockInstructorService);

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;

beforeEach(() => {
  vi.resetAllMocks();
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(async () => {
  await act(async () => {
    root?.unmount();
  });
  root = null;
  container.remove();
});

async function renderComponent(element) {
  if (!root) {
    root = createRoot(container);
  }
  await act(async () => {
    root.render(element);
  });
}

const changeText = (input, value) => {
  const prototype = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, 'value').set.call(input, value);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
};

const toggleCheckbox = (input, checked) => {
  if (input.checked !== checked) {
    input.click();
  }
};

describe('FE-07.1 InstructorSetupForm', () => {
  it('renders all 3 sections and default values correctly without context banner', async () => {
    await renderComponent(<InstructorSetupForm />);

    // 1. Notice banner is removed per design update
    expect(container.textContent).not.toContain('Pemberitahuan Konteks AI');
    expect(container.textContent).not.toContain('tidak menggantikan atau mengubah fakta akademik');

    // 2. Section 1: Instructor Profile
    expect(container.textContent).toContain('1. Profil Pengajar');
    const teachingStyle = container.querySelector('textarea[name="teaching_style"]');
    const expertise = container.querySelector('input[name="expertise"]');
    const deliveryPreference = container.querySelector('textarea[name="delivery_preference"]');

    expect(teachingStyle).not.toBeNull();
    expect(teachingStyle.value).toBe('');
    expect(expertise).not.toBeNull();
    expect(expertise.value).toBe('');
    expect(deliveryPreference).not.toBeNull();
    expect(deliveryPreference.value).toBe('');

    // 3. Section 2: Additional Prompt & Character counter
    expect(container.textContent).toContain('2. Prompt Tambahan (AI Agent)');
    const additionalPrompt = container.querySelector('textarea[name="additional_prompt"]');
    expect(additionalPrompt).not.toBeNull();
    expect(additionalPrompt.value).toBe('');

    const charCounter = container.querySelector('[data-testid="prompt-char-counter"]');
    expect(charCounter).not.toBeNull();
    expect(charCounter.textContent).toContain(`0 / ${MAX_PROMPT_LENGTH} karakter`);

    // 4. Section 3: Activity Configuration
    expect(container.textContent).toContain('3. Konfigurasi Aktivitas Pembelajaran');
    const learningMaterial = container.querySelector('input[name="learning_material"]');
    const learningResource = container.querySelector('input[name="learning_resource"]');
    const assignment = container.querySelector('input[name="assignment"]');
    const quiz = container.querySelector('input[name="quiz"]');

    expect(learningMaterial).not.toBeNull();
    expect(learningMaterial.checked).toBe(DEFAULT_ACTIVITY_CONFIGURATION.learning_material); // true
    expect(learningResource).not.toBeNull();
    expect(learningResource.checked).toBe(DEFAULT_ACTIVITY_CONFIGURATION.learning_resource); // false
    expect(assignment).not.toBeNull();
    expect(assignment.checked).toBe(DEFAULT_ACTIVITY_CONFIGURATION.assignment); // false
    expect(quiz).not.toBeNull();
    expect(quiz.checked).toBe(DEFAULT_ACTIVITY_CONFIGURATION.quiz); // false

    // 5. Actions
    const submitBtn = container.querySelector('button[type="submit"]');
    const cancelBtn = container.querySelector('button[type="button"]');
    expect(submitBtn).not.toBeNull();
    expect(submitBtn.textContent).toContain('Simpan profil');
    expect(cancelBtn).not.toBeNull();
    expect(cancelBtn.textContent).toContain('Batal');
  });

  it('handles null and undefined initial props gracefully without throwing', async () => {
    await renderComponent(<InstructorSetupForm initial={null} />);
    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('');
    expect(container.querySelector('input[name="learning_material"]').checked).toBe(true);

    await renderComponent(<InstructorSetupForm initial={undefined} />);
    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('');
    expect(container.querySelector('input[name="learning_material"]').checked).toBe(true);
  });

  it('renders spinner when loading prop is true', async () => {
    await renderComponent(<InstructorSetupForm loading={true} />);
    const spinner = container.querySelector('[role="status"]');
    expect(spinner).not.toBeNull();
    expect(spinner.textContent).toContain('Memuat profil pengajar…');
    expect(container.querySelector('form')).toBeNull();
  });

  it('populates fields from custom initial props with nested DTO', async () => {
    const initial = {
      instructor_profile: {
        teaching_style: 'Studi kasus interaktif',
        expertise: 'Kecerdasan Buatan',
        delivery_preference: 'Penjelasan konsep secara bertahap',
      },
      additional_prompt: 'Perbanyak analogi dunia nyata.',
      activity_configuration: {
        learning_material: true,
        learning_resource: true,
        assignment: false,
        quiz: true,
      },
    };

    await renderComponent(<InstructorSetupForm initial={initial} />);

    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('Studi kasus interaktif');
    expect(container.querySelector('input[name="expertise"]').value).toBe('Kecerdasan Buatan');
    expect(container.querySelector('textarea[name="delivery_preference"]').value).toBe('Penjelasan konsep secara bertahap');
    expect(container.querySelector('textarea[name="additional_prompt"]').value).toBe('Perbanyak analogi dunia nyata.');

    const charCounter = container.querySelector('[data-testid="prompt-char-counter"]');
    expect(charCounter.textContent).toBe(`${initial.additional_prompt.length} / ${MAX_PROMPT_LENGTH} karakter`);

    expect(container.querySelector('input[name="learning_material"]').checked).toBe(true);
    expect(container.querySelector('input[name="learning_resource"]').checked).toBe(true);
    expect(container.querySelector('input[name="assignment"]').checked).toBe(false);
    expect(container.querySelector('input[name="quiz"]').checked).toBe(true);
  });

  it('populates fields from legacy flat initial props fallback', async () => {
    const initial = {
      teaching_style: 'Kuliah klasikal',
      expertise: 'Algoritma',
      delivery_preference: 'Slide presentasi terstruktur',
      additional_prompt: 'Fokus pemahaman dasar.',
      activity_configuration: {
        learning_material: true,
        learning_resource: false,
        assignment: true,
        quiz: false,
      },
    };

    await renderComponent(<InstructorSetupForm initial={initial} />);

    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('Kuliah klasikal');
    expect(container.querySelector('input[name="expertise"]').value).toBe('Algoritma');
    expect(container.querySelector('textarea[name="delivery_preference"]').value).toBe('Slide presentasi terstruktur');
    expect(container.querySelector('textarea[name="additional_prompt"]').value).toBe('Fokus pemahaman dasar.');
    expect(container.querySelector('input[name="assignment"]').checked).toBe(true);
  });

  it('updates character counter in real time when typing in additional prompt', async () => {
    await renderComponent(<InstructorSetupForm />);

    const promptTextarea = container.querySelector('textarea[name="additional_prompt"]');
    const charCounter = container.querySelector('[data-testid="prompt-char-counter"]');

    expect(charCounter.textContent).toBe(`0 / ${MAX_PROMPT_LENGTH} karakter`);

    await act(async () => {
      changeText(promptTextarea, 'Halo AI, tolong sertakan latihan koding.');
    });

    expect(charCounter.textContent).toBe(`40 / ${MAX_PROMPT_LENGTH} karakter`);
    expect(charCounter.className).not.toContain('text-danger');

    const longText = 'A'.repeat(1001);
    await act(async () => {
      changeText(promptTextarea, longText);
    });

    expect(charCounter.textContent).toBe(`1001 / ${MAX_PROMPT_LENGTH} karakter`);
    expect(charCounter.className).toContain('text-danger');
  });

  it('correctly handles Unicode surrogate pairs and emojis in character counter and validation', async () => {
    await renderComponent(<InstructorSetupForm />);

    const promptTextarea = container.querySelector('textarea[name="additional_prompt"]');
    const charCounter = container.querySelector('[data-testid="prompt-char-counter"]');

    // Emoji '🎓' is 2 UTF-16 code units but 1 Unicode code point
    await act(async () => {
      changeText(promptTextarea, '🎓'.repeat(10));
    });

    expect(charCounter.textContent).toBe(`10 / ${MAX_PROMPT_LENGTH} karakter`);
    expect(charCounter.className).not.toContain('text-danger');

    // 1001 Unicode code points
    await act(async () => {
      changeText(promptTextarea, '🎓'.repeat(1001));
    });

    expect(charCounter.textContent).toBe(`1001 / ${MAX_PROMPT_LENGTH} karakter`);
    expect(charCounter.className).toContain('text-danger');

    const onSubmit = vi.fn();
    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} initial={{ additional_prompt: '🎓'.repeat(1001) }} />);

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).not.toHaveBeenCalled();
    expect(container.querySelector('#additional_prompt_error')).not.toBeNull();
  });

  it('rejects submission when all activities are inactive and displays inline error with aria attributes', async () => {
    const onSubmit = vi.fn();
    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

    const learningMaterial = container.querySelector('input[name="learning_material"]');
    expect(learningMaterial.checked).toBe(true);

    // Uncheck the only active default activity
    await act(async () => {
      toggleCheckbox(learningMaterial, false);
    });

    expect(learningMaterial.checked).toBe(false);
    expect(container.querySelector('input[name="learning_resource"]').checked).toBe(false);
    expect(container.querySelector('input[name="assignment"]').checked).toBe(false);
    expect(container.querySelector('input[name="quiz"]').checked).toBe(false);

    // Submit form
    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).not.toHaveBeenCalled();

    // Inline error displayed under activity section
    const errorEl = container.querySelector('#activity_configuration_error');
    expect(errorEl).not.toBeNull();
    expect(errorEl.textContent).toContain('Minimal satu jenis aktivitas pembelajaran harus diaktifkan');

    const fieldset = container.querySelector('fieldset.checks');
    expect(fieldset.getAttribute('aria-invalid')).toBe('true');
    expect(fieldset.getAttribute('aria-describedby')).toBe('activity_configuration_error');

    // Toggling an activity back on clears the error
    const quiz = container.querySelector('input[name="quiz"]');
    await act(async () => {
      toggleCheckbox(quiz, true);
    });

    expect(container.querySelector('#activity_configuration_error')).toBeNull();

    // Now submit succeeds
    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('rejects submission when additional prompt exceeds limit and preserves error until within limit', async () => {
    const onSubmit = vi.fn();
    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

    const promptTextarea = container.querySelector('textarea[name="additional_prompt"]');

    // Enter prompt longer than 1000 characters
    await act(async () => {
      changeText(promptTextarea, 'X'.repeat(1005));
    });

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).not.toHaveBeenCalled();

    const promptError = container.querySelector('#additional_prompt_error');
    expect(promptError).not.toBeNull();
    expect(promptError.textContent).toContain(`Prompt tambahan tidak boleh melebihi ${MAX_PROMPT_LENGTH} karakter`);
    expect(promptTextarea.getAttribute('aria-invalid')).toBe('true');
    expect(promptTextarea.className).toContain('border-danger');

    // Edit but still over limit: error remains!
    await act(async () => {
      changeText(promptTextarea, 'X'.repeat(1002));
    });
    expect(container.querySelector('#additional_prompt_error')).not.toBeNull();

    // Truncate to within limit: error clears!
    await act(async () => {
      changeText(promptTextarea, 'X'.repeat(999));
    });

    expect(container.querySelector('#additional_prompt_error')).toBeNull();
    expect(promptTextarea.getAttribute('aria-invalid')).toBeNull();

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it('displays error alert when onSubmit rejects and dismisses it on close', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('Gagal menyimpan profil ke server'));
    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);

    const alertEl = container.querySelector('[role="alert"]');
    expect(alertEl).not.toBeNull();
    expect(alertEl.textContent).toContain('Gagal menyimpan profil ke server');

    // Click dismiss button on alert
    const closeBtn = alertEl.querySelector('button[aria-label="Tutup"]');
    expect(closeBtn).not.toBeNull();
    await act(async () => {
      closeBtn.click();
    });

    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it('calls onSubmit with expected payload structure when form is valid', async () => {
    const onSubmit = vi.fn().mockResolvedValue({ success: true });
    const onSaved = vi.fn();

    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} onSaved={onSaved} />);

    await act(async () => {
      changeText(container.querySelector('textarea[name="teaching_style"]'), 'Interaktif, problem-based learning');
      changeText(container.querySelector('input[name="expertise"]'), 'Software Engineering & Cloud Computing');
      changeText(container.querySelector('textarea[name="delivery_preference"]'), 'Banyak studi kasus dunia kerja');
      changeText(container.querySelector('textarea[name="additional_prompt"]'), 'Sertakan contoh dengan Docker dan microservices.');
      toggleCheckbox(container.querySelector('input[name="learning_resource"]'), true);
      toggleCheckbox(container.querySelector('input[name="quiz"]'), true);
    });

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      instructor_profile: {
        teaching_style: 'Interaktif, problem-based learning',
        expertise: 'Software Engineering & Cloud Computing',
        delivery_preference: 'Banyak studi kasus dunia kerja',
        language_preference: 'Bahasa Indonesia',
      },
      additional_prompt: 'Sertakan contoh dengan Docker dan microservices.',
      activity_configuration: {
        learning_material: true,
        learning_resource: true,
        assignment: false,
        quiz: true,
      },
    });

    expect(onSaved).toHaveBeenCalledWith({ success: true });
    expect(container.textContent).toContain('Profil tersimpan.');
  });

  it('reverts to initial values when cancel/reset button is clicked', async () => {
    const initial = {
      teaching_style: 'Awal',
      expertise: 'Keahlian Awal',
      delivery_preference: 'Preferensi Awal',
      additional_prompt: 'Prompt Awal',
      activity_configuration: {
        learning_material: true,
        learning_resource: false,
        assignment: false,
        quiz: false,
      },
    };
    const onReset = vi.fn();

    await renderComponent(<InstructorSetupForm initial={initial} onReset={onReset} />);

    // Modify values
    await act(async () => {
      changeText(container.querySelector('textarea[name="teaching_style"]'), 'Diubah');
      changeText(container.querySelector('input[name="expertise"]'), 'Keahlian Baru');
      changeText(container.querySelector('textarea[name="additional_prompt"]'), 'Prompt Baru yang Lebih Panjang');
      toggleCheckbox(container.querySelector('input[name="assignment"]'), true);
    });

    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('Diubah');
    expect(container.querySelector('input[name="expertise"]').value).toBe('Keahlian Baru');
    expect(container.querySelector('input[name="assignment"]').checked).toBe(true);

    // Click Batal
    const cancelBtn = container.querySelector('button[type="button"]');
    await act(async () => {
      cancelBtn.click();
    });

    expect(onReset).toHaveBeenCalledTimes(1);
    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('Awal');
    expect(container.querySelector('input[name="expertise"]').value).toBe('Keahlian Awal');
    expect(container.querySelector('textarea[name="delivery_preference"]').value).toBe('Preferensi Awal');
    expect(container.querySelector('textarea[name="additional_prompt"]').value).toBe('Prompt Awal');
    expect(container.querySelector('input[name="learning_material"]').checked).toBe(true);
    expect(container.querySelector('input[name="assignment"]').checked).toBe(false);
    expect(container.querySelector('[data-testid="prompt-char-counter"]').textContent).toBe(`11 / ${MAX_PROMPT_LENGTH} karakter`);
  });

  it('disables submit button and controls when saving is in progress and shows loading spinner inside submit button', async () => {
    let resolveSubmit;
    const pendingPromise = new Promise((resolve) => {
      resolveSubmit = resolve;
    });
    const onSubmit = vi.fn().mockReturnValue(pendingPromise);

    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

    const submitBtn = container.querySelector('button[type="submit"]');
    const cancelBtn = container.querySelector('button[type="button"]');
    const promptInput = container.querySelector('textarea[name="additional_prompt"]');

    expect(submitBtn.disabled).toBe(false);
    expect(submitBtn.textContent).toContain('Simpan profil');

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(submitBtn.disabled).toBe(true);
    expect(submitBtn.textContent).toContain('Menyimpan…');
    expect(submitBtn.querySelector('.animate-spin')).not.toBeNull();
    expect(cancelBtn.disabled).toBe(true);
    expect(promptInput.disabled).toBe(true);

    await act(async () => {
      resolveSubmit({ ok: true });
    });

    expect(submitBtn.disabled).toBe(false);
    expect(submitBtn.textContent).toContain('Simpan profil');
    expect(container.textContent).toContain('Profil tersimpan.');
  });

  it('integrates with TeachingPreferencesCard seamlessly', async () => {
    mockInstructorService.getInstructorSetup.mockResolvedValue({
      instructor_profile: {
        teaching_style: 'Diskusi aktif',
        expertise: 'Basis Data',
        delivery_preference: 'Banyak latihan query',
        language_preference: 'Bahasa Indonesia',
      },
      additional_prompt: 'Fokus pada PostgreSQL',
      activity_configuration: {
        learning_material: true,
        learning_resource: true,
        assignment: false,
        quiz: false,
      },
      updated_at: '2026-10-20T10:00:00Z',
    });

    await renderComponent(<TeachingPreferencesCard />);

    // Wait for data load
    expect(container.textContent).toContain('Preferensi mengajar (Generator AI)');
    expect(container.textContent).toContain('Dipakai agent saat menyusun rencana dan konten untuk semua kursus Anda.');
    expect(container.querySelector('textarea[name="teaching_style"]').value).toBe('Diskusi aktif');
    expect(container.querySelector('input[name="expertise"]').value).toBe('Basis Data');
    expect(container.querySelector('textarea[name="delivery_preference"]').value).toBe('Banyak latihan query');
    expect(container.querySelector('textarea[name="additional_prompt"]').value).toBe('Fokus pada PostgreSQL');
    expect(container.querySelector('input[name="learning_material"]').checked).toBe(true);
    expect(container.querySelector('input[name="learning_resource"]').checked).toBe(true);
  });

  it('automatically dismisses "Profil tersimpan." notification after timeout', async () => {
    vi.useFakeTimers();
    try {
      const onSubmit = vi.fn().mockResolvedValue({ success: true });
      await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

      const form = container.querySelector('form');
      await act(async () => {
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      });

      expect(container.textContent).toContain('Profil tersimpan.');

      // Advance timers by 4000ms
      await act(async () => {
        vi.advanceTimersByTime(4000);
      });

      expect(container.textContent).not.toContain('Profil tersimpan.');
    } finally {
      vi.useRealTimers();
    }
  });

  it('maps backend 422 INVALID_REQUEST error details to inline field errors and top alert', async () => {
    const error422 = new Error('Data request tidak valid.');
    error422.status = 422;
    error422.code = 'INVALID_REQUEST';
    error422.details = [
      { field: 'activity_configuration', message: 'Minimal satu jenis aktivitas pembelajaran harus aktif.' },
      { field: 'additional_prompt', message: 'maksimal 2000 karakter' },
      { field: 'instructor_profile.teaching_style', message: 'Gaya mengajar harus berupa teks.' },
    ];

    const onSubmit = vi.fn().mockRejectedValue(error422);
    await renderComponent(<InstructorSetupForm onSubmit={onSubmit} />);

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(onSubmit).toHaveBeenCalledTimes(1);

    // Top alert shows error message
    const alertEl = container.querySelector('[role="alert"]');
    expect(alertEl).not.toBeNull();
    expect(alertEl.textContent).toContain('Data request tidak valid.');

    // Inline errors on individual fields
    const activityErr = container.querySelector('#activity_configuration_error');
    expect(activityErr).not.toBeNull();
    expect(activityErr.textContent).toContain('Minimal satu jenis aktivitas pembelajaran harus aktif.');

    const promptErr = container.querySelector('#additional_prompt_error');
    expect(promptErr).not.toBeNull();
    expect(promptErr.textContent).toContain('maksimal 2000 karakter');

    const teachingStyleErr = container.querySelector('#teaching_style_error');
    expect(teachingStyleErr).not.toBeNull();
    expect(teachingStyleErr.textContent).toContain('Gaya mengajar harus berupa teks.');

    const teachingStyleInput = container.querySelector('textarea[name="teaching_style"]');
    expect(teachingStyleInput.getAttribute('aria-invalid')).toBe('true');
  });

  it('saves via updateInstructorSetup default hook when no onSubmit prop is provided', async () => {
    const onSaved = vi.fn();
    mockInstructorService.updateInstructorSetup.mockResolvedValueOnce({
      instructor_profile: {
        teaching_style: 'Inkuiri',
        expertise: 'Jaringan',
        delivery_preference: 'Praktikum lab',
        language_preference: 'Bahasa Indonesia',
      },
      additional_prompt: 'Gunakan Wireshark.',
      activity_configuration: {
        learning_material: true,
        learning_resource: false,
        assignment: false,
        quiz: false,
      },
      updated_at: '2026-10-27T10:00:00Z',
    });

    await renderComponent(<InstructorSetupForm onSaved={onSaved} />);

    await act(async () => {
      changeText(container.querySelector('textarea[name="teaching_style"]'), 'Inkuiri');
      changeText(container.querySelector('textarea[name="additional_prompt"]'), 'Gunakan Wireshark.');
    });

    await act(async () => {
      container.querySelector('form').requestSubmit();
    });

    expect(mockInstructorService.updateInstructorSetup).toHaveBeenCalledTimes(1);
    expect(mockInstructorService.updateInstructorSetup).toHaveBeenCalledWith(
      expect.objectContaining({
        instructor_profile: expect.objectContaining({
          teaching_style: 'Inkuiri',
        }),
        additional_prompt: 'Gunakan Wireshark.',
      })
    );
    expect(onSaved).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain('Profil tersimpan.');
  });

  it('provides backward compatibility via TeachingProfileForm wrapper', async () => {
    await renderComponent(<TeachingProfileForm />);
    expect(container.textContent).toContain('1. Profil Pengajar');
    expect(container.textContent).toContain('2. Prompt Tambahan (AI Agent)');
    expect(container.textContent).toContain('3. Konfigurasi Aktivitas Pembelajaran');
  });
});
