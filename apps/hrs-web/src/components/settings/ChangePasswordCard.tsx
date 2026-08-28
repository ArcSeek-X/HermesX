import type React from 'react';
import { useState } from 'react';
import type { ParsedApiError } from '../../api/error';
import { isParsedApiError } from '../../api/error';
import { useAuth } from '../../hooks';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { Button, PasswordInput } from '../';
import { SettingsAlert } from './SettingsAlert';
import { SettingsSectionCard } from './SettingsSectionCard';

export const ChangePasswordCard: React.FC = () => {
  const { changePassword } = useAuth();
  const { t } = useUiLanguage();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | ParsedApiError | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!currentPassword.trim()) {
      setError(t('settings.changePasswordRequiredCurrent'));
      return;
    }
    if (!newPassword.trim()) {
      setError(t('settings.changePasswordRequiredNew'));
      return;
    }
    if (newPassword.length < 6) {
      setError(t('settings.changePasswordShort'));
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setError(t('auth.login.passwordMismatch'));
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await changePassword(currentPassword, newPassword, newPasswordConfirm);
      if (result.success) {
        setSuccess(true);
        setCurrentPassword('');
        setNewPassword('');
        setNewPasswordConfirm('');
        setTimeout(() => setSuccess(false), 4000);
      } else {
        setError(result.error ?? t('settings.changePasswordFailure'));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <SettingsSectionCard
      title={t('settings.changePasswordTitle')}
      description={t('settings.changePasswordDescription')}
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <label htmlFor="change-pass-current" className="mb-2 block text-sm font-medium text-foreground">{t('settings.changePasswordCurrent')}</label>
            <PasswordInput
              id="change-pass-current"
              type="password"
              allowTogglePassword
              iconType="password"
              placeholder={t('settings.changePasswordCurrentPlaceholder')}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={isSubmitting}
              autoComplete="current-password"
            />
          </div>

          <div className="space-y-3">
            <label htmlFor="change-pass-new" className="mb-2 block text-sm font-medium text-foreground">{t('settings.changePasswordNew')}</label>
            <PasswordInput
              id="change-pass-new"
              type="password"
              allowTogglePassword
              iconType="password"
              placeholder={t('settings.changePasswordNewPlaceholder')}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isSubmitting}
              autoComplete="new-password"
            />
            <p className="mt-2 text-xs text-secondary-text">{t('settings.changePasswordNewHint')}</p>
          </div>
        </div>

        <div className="space-y-3 md:max-w-md">
          <label htmlFor="change-pass-confirm" className="mb-2 block text-sm font-medium text-foreground">{t('settings.changePasswordConfirm')}</label>
          <PasswordInput
            id="change-pass-confirm"
            type="password"
            allowTogglePassword
            iconType="password"
            placeholder={t('settings.changePasswordConfirmPlaceholder')}
            value={newPasswordConfirm}
            onChange={(e) => setNewPasswordConfirm(e.target.value)}
            disabled={isSubmitting}
            autoComplete="new-password"
          />
        </div>

        {error
          ? isParsedApiError(error)
            ? <SettingsAlert title={t('settings.changePasswordFailure')} message={error.message} variant="error" className="!mt-3" />
            : <SettingsAlert title={t('settings.changePasswordFailure')} message={error} variant="error" className="!mt-3" />
          : null}
        {success ? (
          <SettingsAlert title={t('settings.changePasswordSuccess')} message={t('settings.changePasswordSuccessMessage')} variant="success" />
        ) : null}

        <Button type="submit" variant="primary" isLoading={isSubmitting}>
          {t('settings.changePasswordSave')}
        </Button>
      </form>
    </SettingsSectionCard>
  );
};
