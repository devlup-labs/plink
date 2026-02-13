class SignalingManager {
  constructor(webrtcConnection, metadataManager) {
    this.webrtcConnection = webrtcConnection;
    this.metadataManager = metadataManager;
    this.role = null; // 'sender' or 'receiver'
    this.fileMetadata = null;
    this.localMetadata = null;
    this.remoteMetadata = null;
    this.connectionState = 'idle'; // 'idle', 'preparing', 'waiting', 'connecting', 'connected', 'failed'
  }

  /**
   * Initiates connection as sender
   * @param {Object} fileMetadata - File metadata
   * @returns {Promise<string>} - Metadata to share
   */
  async initiateSender(fileMetadata) {
    try {
      this.role = 'sender';
      this.fileMetadata = fileMetadata;
      this.connectionState = 'preparing';

      console.log('Initiating sender with file:', fileMetadata);

      // Initialize WebRTC connection as initiator
      await this.webrtcConnection.initialize(true);

      // Create WebRTC offer
      const offerData = await this.webrtcConnection.createOffer();
      console.log('Created WebRTC offer');

      // Create metadata payload combining file info and WebRTC data
      const metadataPayload = {
        version: "1.0",
        role: "sender",
        file: {
          fileName: fileMetadata.fileName,
          fileSize: fileMetadata.fileSize,
          totalChunks: fileMetadata.totalChunks,
          chunkSize: fileMetadata.chunkSize,
          fileType: fileMetadata.fileType,
          checksum: fileMetadata.checksum
        },
        webrtc: {
          sdp: offerData.sdp,
          type: offerData.type,
          iceCandidates: offerData.iceCandidates
        },
        timestamp: Date.now()
      };

      // Use MetadataManager to create shareable string
      const shareableMetadata = this.metadataManager.createMetadataPayload(
        metadataPayload.file,
        offerData.iceCandidates,
        {
          sdp: offerData.sdp,
          type: offerData.type
        }
      );

      this.localMetadata = metadataPayload;
      this.connectionState = 'waiting';

      console.log('Sender metadata created successfully');
      return shareableMetadata;

    } catch (error) {
      console.error('Error initiating sender:', error);
      this.connectionState = 'failed';
      throw new Error(`Failed to initiate sender: ${error.message}`);
    }
  }

  /**
   * Initiates connection as receiver
   * @param {string} senderMetadata - Received metadata
   * @returns {Promise<string>} - Response metadata
   */
  async initiateReceiver(senderMetadata) {
    try {
      this.role = 'receiver';
      this.connectionState = 'preparing';

      console.log('Initiating receiver with sender metadata');

      // Parse sender's metadata
      const parsedMetadata = this.metadataManager.parseMetadataPayload(senderMetadata);
      
      if (!parsedMetadata || parsedMetadata.role !== 'sender') {
        throw new Error('Invalid sender metadata');
      }

      this.remoteMetadata = parsedMetadata;
      this.fileMetadata = parsedMetadata.file;

      console.log('Parsed sender metadata:', {
        fileName: this.fileMetadata.fileName,
        fileSize: this.fileMetadata.fileSize,
        totalChunks: this.fileMetadata.totalChunks
      });

      // Initialize WebRTC connection as non-initiator
      await this.webrtcConnection.initialize(false);

      // Create answer to sender's offer
      const answerData = await this.webrtcConnection.createAnswer(parsedMetadata.webrtc.sdp);
      console.log('Created WebRTC answer');

      // Add sender's ICE candidates
      if (parsedMetadata.webrtc.iceCandidates && parsedMetadata.webrtc.iceCandidates.length > 0) {
        for (const candidate of parsedMetadata.webrtc.iceCandidates) {
          await this.webrtcConnection.addIceCandidate(candidate);
        }
        console.log(`Added ${parsedMetadata.webrtc.iceCandidates.length} ICE candidates`);
      }

      // Create response metadata payload
      const responsePayload = {
        version: "1.0",
        role: "receiver",
        webrtc: {
          sdp: answerData.sdp,
          type: answerData.type,
          iceCandidates: answerData.iceCandidates
        },
        timestamp: Date.now()
      };

      // Use MetadataManager to create shareable response
      const shareableResponse = this.metadataManager.createMetadataPayload(
        null, // No file info for receiver
        answerData.iceCandidates,
        {
          sdp: answerData.sdp,
          type: answerData.type
        }
      );

      this.localMetadata = responsePayload;
      this.connectionState = 'waiting';

      console.log('Receiver response metadata created successfully');
      return shareableResponse;

    } catch (error) {
      console.error('Error initiating receiver:', error);
      this.connectionState = 'failed';
      throw new Error(`Failed to initiate receiver: ${error.message}`);
    }
  }

  /**
   * Completes connection with remote metadata
   * @param {string} remoteMetadata - Remote peer metadata
   * @returns {Promise<void>}
   */
  async completeConnection(remoteMetadata) {
    try {
      this.connectionState = 'connecting';

      console.log('Completing connection with remote metadata');

      // Parse remote metadata
      const parsedRemote = this.metadataManager.parseMetadataPayload(remoteMetadata);
      
      if (!parsedRemote || !parsedRemote.webrtc) {
        throw new Error('Invalid remote metadata');
      }

      // Validate role compatibility
      if (this.role === 'sender' && parsedRemote.role !== 'receiver') {
        throw new Error('Role mismatch: expected receiver metadata');
      }
      if (this.role === 'receiver' && parsedRemote.role !== 'sender') {
        throw new Error('Role mismatch: expected sender metadata');
      }

      this.remoteMetadata = parsedRemote;

      // Set remote description
      await this.webrtcConnection.setRemoteDescription({
        type: parsedRemote.webrtc.type,
        sdp: parsedRemote.webrtc.sdp
      });

      console.log('Set remote description');

      // Add remote ICE candidates
      if (parsedRemote.webrtc.iceCandidates && parsedRemote.webrtc.iceCandidates.length > 0) {
        for (const candidate of parsedRemote.webrtc.iceCandidates) {
          await this.webrtcConnection.addIceCandidate(candidate);
        }
        console.log(`Added ${parsedRemote.webrtc.iceCandidates.length} remote ICE candidates`);
      }

      // Wait for connection to establish
      await this._waitForConnection();

      this.connectionState = 'connected';
      console.log('Connection completed successfully');

    } catch (error) {
      console.error('Error completing connection:', error);
      this.connectionState = 'failed';
      throw new Error(`Failed to complete connection: ${error.message}`);
    }
  }

  /**
   * Waits for WebRTC connection to establish
   * @returns {Promise<void>}
   * @private
   */
  _waitForConnection() {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, 10000); // 10 second timeout

      const checkConnection = () => {
        const stats = this.webrtcConnection.getDataChannelState();
        const connectionState = this.webrtcConnection.peerConnection?.connectionState;

        console.log('Connection state:', connectionState, 'Data channel:', stats);

        if (stats === 'open') {
          clearTimeout(timeout);
          resolve();
        } else if (connectionState === 'failed' || connectionState === 'closed') {
          clearTimeout(timeout);
          reject(new Error('Connection failed'));
        } else {
          setTimeout(checkConnection, 100); // Check every 100ms
        }
      };

      checkConnection();
    });
  }

  /**
   * Handles connection state changes
   * @param {string} state - Connection state
   * @returns {void}
   */
  handleConnectionState(state) {
    console.log('Connection state changed:', state);

    switch (state) {
      case 'connected':
      case 'completed':
        if (this.connectionState === 'connecting') {
          this.connectionState = 'connected';
        }
        break;

      case 'disconnected':
        this.connectionState = 'disconnected';
        break;

      case 'failed':
      case 'closed':
        this.connectionState = 'failed';
        break;

      case 'datachannel-open':
        console.log('Data channel is now open and ready for file transfer');
        if (this.connectionState === 'connecting') {
          this.connectionState = 'connected';
        }
        break;

      case 'datachannel-closed':
        console.log('Data channel closed');
        break;

      case 'datachannel-error':
        console.error('Data channel error occurred');
        this.connectionState = 'failed';
        break;

      default:
        console.log('Unhandled connection state:', state);
    }
  }

  /**
   * Gets current connection status
   * @returns {Object} - Connection status information
   */
  getConnectionStatus() {
    return {
      role: this.role,
      connectionState: this.connectionState,
      hasFileMetadata: !!this.fileMetadata,
      hasLocalMetadata: !!this.localMetadata,
      hasRemoteMetadata: !!this.remoteMetadata,
      webrtcState: this.webrtcConnection.peerConnection?.connectionState || 'not-initialized',
      dataChannelState: this.webrtcConnection.getDataChannelState(),
      fileInfo: this.fileMetadata ? {
        fileName: this.fileMetadata.fileName,
        fileSize: this.fileMetadata.fileSize,
        totalChunks: this.fileMetadata.totalChunks
      } : null
    };
  }

  /**
   * Checks if connection is ready for file transfer
   * @returns {boolean} - True if ready for transfer
   */
  isReadyForTransfer() {
    return this.connectionState === 'connected' && 
           this.webrtcConnection.getDataChannelState() === 'open';
  }

  /**
   * Gets file metadata (for receiver to display file info)
   * @returns {Object|null} - File metadata or null
   */
  getFileMetadata() {
    return this.fileMetadata;
  }

  /**
   * Resets connection
   * @returns {void}
   */
  reset() {
    console.log('Resetting signaling manager');
    
    // Close WebRTC connection
    if (this.webrtcConnection) {
      this.webrtcConnection.close();
    }

    // Reset all state
    this.role = null;
    this.fileMetadata = null;
    this.localMetadata = null;
    this.remoteMetadata = null;
    this.connectionState = 'idle';

    console.log('Signaling manager reset complete');
  }

  /**
   * Gets detailed connection statistics
   * @returns {Promise<Object>} - Detailed stats
   */
  async getDetailedStats() {
    const webrtcStats = await this.webrtcConnection.getStats();
    
    return {
      signaling: {
        role: this.role,
        connectionState: this.connectionState,
        hasFileMetadata: !!this.fileMetadata,
        fileSize: this.fileMetadata?.fileSize || 0,
        totalChunks: this.fileMetadata?.totalChunks || 0
      },
      webrtc: webrtcStats,
      timestamp: Date.now()
    };
  }
}