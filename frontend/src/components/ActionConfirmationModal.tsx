import { PendingAction } from "../api/chat";

type ActionConfirmationModalProps = {
  pendingAction: PendingAction | null;
  onConfirm: (actionId: string) => void;
  onCancel: () => void;
};

export function ActionConfirmationModal({
  pendingAction,
  onConfirm,
  onCancel,
}: ActionConfirmationModalProps) {
  if (!pendingAction) return null;

  return (
    <div className="action-confirmation-dialog" role="alertdialog" aria-modal="true">
      <div className="action-confirmation-content">
        <div className="action-warning-badge">HIGH-IMPACT ACTION REQUIRED</div>
        <h3>{pendingAction.label}</h3>
        <p>{pendingAction.description}</p>

        {pendingAction.arguments && Object.keys(pendingAction.arguments).length > 0 && (
          <div className="action-parameters">
            <span className="params-label">TARGET PARAMETERS:</span>
            <pre>{JSON.stringify(pendingAction.arguments, null, 2)}</pre>
          </div>
        )}

        <div className="action-button-group">
          <button
            type="button"
            className="action-confirm-btn"
            onClick={() => onConfirm(pendingAction.actionId)}
          >
            Authorize & Execute
          </button>
          <button type="button" className="action-cancel-btn" onClick={onCancel}>
            Cancel Action
          </button>
        </div>
      </div>
    </div>
  );
}
