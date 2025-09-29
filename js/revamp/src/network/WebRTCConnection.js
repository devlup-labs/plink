class WebRTCConnection {
  constructor(onDataChannelMessage, onConnectionStateChange) {
    this.peerConnection = null;
    this.dataChannel = null;
    this.onDataChannelMessage = onDataChannelMessage;
    this.onConnectionStateChange = onConnectionStateChange;
    this.iceCandidates = [];
    this.isInitiator = false;
    this.remoteDataChannel = null;
  }

  /**
   * Initializes peer connection
   * @param {boolean} isInitiator - True if sender
   * @returns {Promise<void>}
   */
  async initialize(isInitiator) {
    this.isInitiator = isInitiator;
    
    // Configuration for ICE servers (STUN/TURN)
    const configuration = {
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
      ]
    };

    this.peerConnection = new RTCPeerConnection(configuration);
    
    // Set up event handlers
    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.iceCandidates.push(event.candidate);
      }
    };

    this.peerConnection.onconnectionstatechange = () => {
      const state = this.peerConnection.connectionState;
      console.log('Connection state change:', state);
      if (this.onConnectionStateChange) {
        this.onConnectionStateChange(state);
      }
    };

    this.peerConnection.oniceconnectionstatechange = () => {
      console.log('ICE connection state:', this.peerConnection.iceConnectionState);
    };

    // If initiator (sender), create data channel
    if (isInitiator) {
      this.dataChannel = this.peerConnection.createDataChannel('fileTransfer', {
        ordered: true,
        maxRetransmits: 3
      });
      this._setupDataChannelHandlers(this.dataChannel);
    } else {
      // If receiver, wait for data channel from remote peer
      this.peerConnection.ondatachannel = (event) => {
        this.remoteDataChannel = event.channel;
        this._setupDataChannelHandlers(this.remoteDataChannel);
      };
    }
  }

  /**
   * Sets up data channel event handlers
   * @param {RTCDataChannel} dataChannel - Data channel to set up
   * @private
   */
  _setupDataChannelHandlers(dataChannel) {
    dataChannel.onopen = () => {
      console.log('Data channel opened');
      if (this.onConnectionStateChange) {
        this.onConnectionStateChange('datachannel-open');
      }
    };

    dataChannel.onclose = () => {
      console.log('Data channel closed');
      if (this.onConnectionStateChange) {
        this.onConnectionStateChange('datachannel-closed');
      }
    };

    dataChannel.onerror = (error) => {
      console.error('Data channel error:', error);
      if (this.onConnectionStateChange) {
        this.onConnectionStateChange('datachannel-error');
      }
    };

    dataChannel.onmessage = (event) => {
      if (this.onDataChannelMessage) {
        try {
          const data = JSON.parse(event.data);
          this.onDataChannelMessage(data);
        } catch (error) {
          console.error('Error parsing data channel message:', error);
        }
      }
    };
  }

  /**
   * Creates offer (for sender)
   * @returns {Promise<Object>} - SDP offer and ICE candidates
   */
  async createOffer() {
    if (!this.peerConnection) {
      throw new Error('Peer connection not initialized');
    }

    // Clear previous ICE candidates
    this.iceCandidates = [];

    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);

    // Wait for ICE gathering to complete
    await this._waitForIceGathering();

    return {
      sdp: offer.sdp,
      type: "offer",
      iceCandidates: [...this.iceCandidates]
    };
  }

  /**
   * Creates answer (for receiver)
   * @param {RTCSessionDescription} offer - Received offer
   * @returns {Promise<Object>} - SDP answer and ICE candidates
   */
  async createAnswer(offer) {
    if (!this.peerConnection) {
      throw new Error('Peer connection not initialized');
    }

    // Clear previous ICE candidates
    this.iceCandidates = [];

    // Set remote description (the offer)
    await this.peerConnection.setRemoteDescription(new RTCSessionDescription({
      type: 'offer',
      sdp: offer
    }));

    // Create answer
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    // Wait for ICE gathering to complete
    await this._waitForIceGathering();

    return {
      sdp: answer.sdp,
      type: "answer",
      iceCandidates: [...this.iceCandidates]
    };
  }

  /**
   * Sets remote description
   * @param {RTCSessionDescription} description - Remote SDP
   * @returns {Promise<void>}
   */
  async setRemoteDescription(description) {
    if (!this.peerConnection) {
      throw new Error('Peer connection not initialized');
    }

    await this.peerConnection.setRemoteDescription(new RTCSessionDescription(description));
  }

  /**
   * Adds ICE candidate
   * @param {RTCIceCandidate} candidate - ICE candidate
   * @returns {Promise<void>}
   */
  async addIceCandidate(candidate) {
    if (!this.peerConnection) {
      throw new Error('Peer connection not initialized');
    }

    try {
      await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (error) {
      console.error('Error adding ICE candidate:', error);
    }
  }

  /**
   * Waits for ICE gathering to complete
   * @returns {Promise<void>}
   * @private
   */
  _waitForIceGathering() {
    return new Promise((resolve) => {
      if (this.peerConnection.iceGatheringState === 'complete') {
        resolve();
        return;
      }

      const timeout = setTimeout(() => {
        this.peerConnection.removeEventListener('icegatheringstatechange', onStateChange);
        resolve(); // Resolve even if not complete to avoid hanging
      }, 3000); // 3 second timeout

      const onStateChange = () => {
        if (this.peerConnection.iceGatheringState === 'complete') {
          clearTimeout(timeout);
          this.peerConnection.removeEventListener('icegatheringstatechange', onStateChange);
          resolve();
        }
      };

      this.peerConnection.addEventListener('icegatheringstatechange', onStateChange);
    });
  }

  /**
   * Sends data through data channel
   * @param {Object} data - Data to send
   * @returns {void}
   */
  sendData(data) {
    const channel = this.dataChannel || this.remoteDataChannel;
    
    if (!channel) {
      console.error('No data channel available');
      return;
    }

    if (channel.readyState !== 'open') {
      console.error('Data channel is not open. State:', channel.readyState);
      return;
    }

    try {
      const jsonString = JSON.stringify(data);
      channel.send(jsonString);
    } catch (error) {
      console.error('Error sending data:', error);
    }
  }

  /**
   * Gets data channel ready state
   * @returns {string} - Ready state of data channel
   */
  getDataChannelState() {
    const channel = this.dataChannel || this.remoteDataChannel;
    return channel ? channel.readyState : 'unavailable';
  }

  /**
   * Closes connection
   * @returns {void}
   */
  close() {
    if (this.dataChannel) {
      this.dataChannel.close();
      this.dataChannel = null;
    }

    if (this.remoteDataChannel) {
      this.remoteDataChannel.close();
      this.remoteDataChannel = null;
    }

    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }

    this.iceCandidates = [];
  }

  /**
   * Gets connection stats
   * @returns {Promise<Object>} - Connection statistics
   */
  async getStats() {
    if (!this.peerConnection) {
      return {
        connectionState: 'closed',
        iceConnectionState: 'closed',
        dataChannelState: 'closed'
      };
    }

    try {
      const stats = await this.peerConnection.getStats();
      const statsReport = {};
      
      stats.forEach((report) => {
        if (report.type === 'data-channel') {
          statsReport.dataChannel = {
            messagesSent: report.messagesSent,
            messagesReceived: report.messagesReceived,
            bytesSent: report.bytesSent,
            bytesReceived: report.bytesReceived
          };
        } else if (report.type === 'candidate-pair' && report.nominated) {
          statsReport.connection = {
            bytesSent: report.bytesSent,
            bytesReceived: report.bytesReceived,
            packetsLost: report.packetsLost,
            currentRoundTripTime: report.currentRoundTripTime
          };
        }
      });

      return {
        connectionState: this.peerConnection.connectionState,
        iceConnectionState: this.peerConnection.iceConnectionState,
        dataChannelState: this.getDataChannelState(),
        ...statsReport
      };
    } catch (error) {
      console.error('Error getting stats:', error);
      return {
        connectionState: this.peerConnection.connectionState,
        iceConnectionState: this.peerConnection.iceConnectionState,
        dataChannelState: this.getDataChannelState(),
        error: error.message
      };
    }
  }
}