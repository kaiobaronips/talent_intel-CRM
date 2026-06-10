import type { Interaction } from '@/lib/types';

type InteractionStatusDisplay = {
  value?: string | null;
  label?: string;
};

function payloadString(interaction: Interaction, key: string) {
  const value = interaction.payload_json?.[key];
  return typeof value === 'string' ? value : undefined;
}

function isExpandiLinkedInDelegated(interaction: Interaction) {
  const status = (interaction.status ?? interaction.interaction_status ?? '').toLowerCase();
  const provider = (interaction.linkedin_provider ?? payloadString(interaction, 'linkedin_provider') ?? '').toLowerCase();
  const executed = interaction.provider_executed ?? interaction.payload_json?.provider_executed;

  return interaction.channel === 'linkedin' && status === 'sent' && provider === 'expandi' && executed === true;
}

export function interactionDisplayStatus(interaction: Interaction): InteractionStatusDisplay {
  if (isExpandiLinkedInDelegated(interaction)) {
    return { value: 'expandi_delegated', label: 'Entregue ao Expandi' };
  }

  return { value: interaction.status ?? interaction.interaction_status };
}

export function providerConfirmationLabel(interaction: Interaction) {
  if (isExpandiLinkedInDelegated(interaction)) {
    return 'O CRM entregou este contato ao Expandi. A confirmação final depende da fila e dos limites do LinkedIn no Expandi.';
  }

  if (interaction.provider_message_id && interaction.channel === 'email') {
    return `Resend ID: ${interaction.provider_message_id}`;
  }

  return null;
}
